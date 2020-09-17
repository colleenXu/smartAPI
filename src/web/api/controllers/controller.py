"""
Controller Classes for
- model.api_doc
Used by web.handlers
"""

import logging
import string
import datetime

from elasticsearch import Elasticsearch
from elasticsearch_dsl import *
from ..model.api_doc import API_Doc
from ..transform import (APIMetadata, decode_raw, get_api_metadata_by_url)
from tornado.httpclient import HTTPError, HTTPResponse

logger = logging.getLogger(__name__)

ES_HOST = 'localhost:9200'
ES_INDEX_NAME = 'smartapi_oas3'


def get_es(es_host=None):

    es_host = es_host or ES_HOST
    es = Elasticsearch(es_host, timeout=120)
    return es

class RegistrationError(Exception):

    fields = ('message', 'path', 'schema_path', 'cause',
              'validator', 'validator_value', 'parent')

    def __init__(self, error):
        self.error = error

    def to_dict(self):
        error = {
            key: self._json_serialize(getattr(self.error, key))
            for key in self.fields
        }
        error['reason'] = error.pop('message')
        return error

    def _json_serialize(self, obj):

        if obj is None:
            return obj
        if isinstance(obj, (str, int, float)):
            return obj
        if isinstance(obj, dict):
            return {key: self._json_serialize(obj[key]) for key in obj}
        if isinstance(obj, (list, deque)):
            return [self._json_serialize(val) for val in obj]
        if isinstance(obj, ValidationError):
            return APIDocValidationError(obj).to_dict()
        raise TypeError(str(type(obj)))

    def __str__(self):
        return self.error.message


class ValidationError(Exception):
    pass


class APIMetadataRegistrationError(Exception):
    pass


class APIDocController:

    def __init__(self, index=None, doc_type=None, es_host=None, _id=None):
        self._es = get_es(es_host)
        self._index = index or ES_INDEX_NAME
        doc = API_Doc()
        self._doc = doc.get(id=_id)

    @staticmethod
    def exists(_id):
        """
        schema: schema namespace
        """
        doc = API_Doc()
        return doc.exists(_id=_id)

    @property
    def user(self):
        return self._doc._meta.github_username

    @property
    def url(self):
        return self._doc._meta.url

    @property
    def slug(self):
        return self._doc._meta.slug

    @staticmethod
    def add(api_doc, save_v2=False, overwrite=False, user_name=None,
            override_owner=False, warn_on_identical=False, dryrun=False):
        """
        Validate metadata provided against openapi or swagger schema
        Check if document exists then
        Check if overwrite settings exist then
        Check if if its just a test run if not
        Save Doc

        Args:
            api_doc (dict): [API metadata]
            save_v2 (bool, optional): [save outdated version]. Defaults to False.
            overwrite (bool, optional): [overwrite existing doc]. Defaults to False.
            user_name ([type], optional): [user.login]. Defaults to None.
            override_owner (bool, optional): [overwite owner]. Defaults to False.
            warn_on_identical (bool, optional): [warn on exact match found]. Defaults to False.
            dryrun (bool, optional): [test registration]. Defaults to False.

        Raises:
            HTTPResponse: [network related issues]

        Returns:
            Returns True if this operations resulted in new document being created.
        """
        metadata = APIMetadata(api_doc)
        # validate document schema
        validation = metadata.validate(raise_error_on_v2=not save_v2)
        if not validation['valid']:
            validation['success'] = False
            validation['error'] = '[Validation] ' + validation['error']
            # return valid
            raise ValidationError(validation)

        # generates an id based on source url
        api_id = metadata.encode_api_id()
        doc_exists = APIDocController.exists(api_id)
        # print("\033[93m"+"API EXISTS: "+"\033[0m", doc_exists)
        if doc_exists:
            if not overwrite:
                # print("\033[93m"+"NOT!!! OVERWRITE: "+"\033[0m", overwrite)
                raise APIMetadataRegistrationError({"success": False, "error": "[Conflict] API exists. Not saved."})
            elif not override_owner:
                # Check user is owner
                i = API_Doc.get(id=api_id).to_dict()
                _owner = i.get('_meta', {}).get('github_username', '')            
                if _owner != user_name:
                    raise APIMetadataRegistrationError({"success": False, "error": "[Conflict] User mismatch. Not Saved."})
                # print("\033[93m"+"API EXISTS AND OWNER IS: "+"\033[0m", _owner)   

        # save to es index
        if dryrun:
            print("\033[93m"+"IS DRYRUN: "+"\033[0m", dryrun)
            logger.info(msg= f"Dryrun for metadata registration at {datetime.today().strftime('%Y-%m-%d')}")
            return False

        # print("\033[93m"+"SAVE NEW: "+"\033[0m")
        # save doc with generated id
        doc = API_Doc(meta={'id': api_id}, ** metadata.convert_es())
        saved = doc.save()
        if saved:
            return True
        else:
            raise RegistrationError('Registration failed')

    @staticmethod
    def get_api(api_name, fields=None, with_meta=True, return_raw=False, size=None, from_=0):


        def _get_hit_object(hit):
            obj = hit.get('fields', hit.get('_source', {}))
            if '_id' in hit:
                obj['_id'] = hit['_id']
            return obj


        def _get_api_doc(api_doc, with_meta=True):
            doc = decode_raw(api_doc.get('~raw', ''))
            if with_meta:
                doc["_meta"] = api_doc.get('_meta', {})
                doc["_id"] = api_doc["_id"]
            return doc

        if api_name == 'all':
            query = {'query': {"bool": {"must_not": {
                "term": {"_meta._archived": "true"}}}}}
        else:
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "_id": {
                                        "query": api_name
                                    }
                                }
                            },
                            {
                                "term": {
                                    "_meta.slug": api_name
                                }
                            }
                        ],
                        "must_not": {"term": {"_meta._archived": "true"}}
                    }
                }
            }
        if fields and fields not in ["all", ["all"]]:
            query["_source"] = fields
        if size and isinstance(size, int):
            query['size'] = min(size, 100)    # set max size to 100 for now.
        if from_ and isinstance(from_, int) and from_ > 0:
            query['from'] = from_
        # res = self._es.search(self._index, query)
        client = Elasticsearch()
        s = Search(using=client)
        s = s.from_dict(query)
        res = s.execute().to_dict()

        if return_raw == '2':
            return res
        res = [_get_hit_object(d) for d in res['hits']['hits']]
        if not return_raw:
            try:
                res = [_get_api_doc(x, with_meta=with_meta) for x in res]
            except ValueError as e:
                res = {'success': False, 'error': str(e)}
        if len(res) == 1:
            res = res[0]
        return res
    

    def get_tags(field=None, size=100):
        """
            return a list of existing values for the given field.
        """
        use_raw = True
        _field = field + ".raw" if use_raw else field
        agg_name = 'field_values'
        doc = API_Doc()
        res = doc.aggregate(field=field, size=size, agg_name=agg_name)
        print(res.to_dict())
        return res.to_dict()

        
    def delete(self, _id, user):
        '''
            delete api from index
            UPDATED TO DSL
        '''
        i = API_Doc.get(id=_id).to_dict()
        _user = i.get('_meta', {}).get('github_username', '')

        # Make sure this is the correct user
        if user.get('login', None) != _user:
            return (405, {"success": False, "error": "User '{}' is not the owner of API '{}'".format(user.get('login', None), _id)})

        self._doc.delete(id=_id)
        Index(API_Doc.Index.name).refresh()
        return (200, {"success": True})

    def update(self, _id, user, slug_name):
        ''' 
            set the slug name of API _id to slug_name. 
             UPDATED TO DSL
        '''
        if not self.exists(_id):
            return (404, {"success": False, "error": "Could not retrieve API '{}' to set slug name".format(_id)})

        i = API_Doc.get(id=_id).to_dict()
        _user = i.get('_meta', {}).get('github_username', '')

        # Make sure this is the correct user
        if user.get('login', None) != _user:
            return (405, {"success": False, "error": "User '{}' is not the owner of API '{}'".format(user.get('login', None), _id)})

        print("\033[93m"+" User matches: "+"\033[0m", _user)
        # validate the slug name
        _valid, _resp = self._validate_slug_name(slug_name=slug_name)

        if not _valid:
            return (405, _resp)

        # doc = API_Doc()
        # doc = doc.get(id=_id)
        self._doc.update(id=_id, refresh=True, _meta={"slug": slug_name.lower()})

        return (200, {"success": True, "{}._meta.slug".format(_id): slug_name.lower()})

    def _validate_slug_name(self, slug_name):
        ''' 
            Function that determines whether slug_name is a valid slug name 
            UPDATED TO DSL
        '''
        _valid_chars = string.ascii_letters + string.digits + "-_~"
        _slug = slug_name.lower()

        # reserved for dev node, normal web functioning
        if _slug in ['www', 'dev', 'smart-api']:
            return (False, {"success": False, "error": "Slug name '{}' is reserved, please choose another".format(_slug)})

        # length requirements
        if len(_slug) < 4 or len(_slug) > 50:
            return (False, {"success": False, "error": "Slug name must be between 4 and 50 chars"})

        # character requirements
        if not all([x in _valid_chars for x in _slug]):
            return (False, {"success": False, "error": "Slug name contains invalid characters.  Valid characters: '{}'".format(_valid_chars)})

        # does it exist already?
        doc = API_Doc()
        if doc.slug_exists(slug=_slug):
            return (False, {"success": False, "error": "Slug name '{}' already exists, please choose another".format(_slug)})

        # good name
        return (True, {})
    
    # def refresh_api(self, api_doc, user=None, override_owner=False, dryrun=True,
    #                  error_on_identical=False, save_v2=False):
    def refresh_api(self, _id, user):
        ''' refresh the given API document object based on its saved metadata url  '''

        doc = API_Doc(id=_id)
        api_doc = doc.get(id=_id).to_dict()
        print("\033[93m"+"DOC TO UPDATE "+"\033[0m", api_doc)

        _meta = api_doc.get('_meta', {})

        res = get_api_metadata_by_url(_meta['url'])
        
        if res and isinstance(res, dict):
            if res.get('success', None) is False:
                res['error'] = '[Request] '+res.get('error', '')
                status = res
            else:
                _meta['timestamp'] = datetime.now().isoformat()
                res['_meta'] = _meta
                print("\033[93m"+"UPDATING DOC WITH ID "+"\033[0m", _id)
                print("\033[93m"+"NEW META "+"\033[0m", res['_meta'])
                self._doc.update(id=_id, refresh=True, _meta=res['_meta'])
                status = (200, {'success': True, 'error': 'None'})
        else:
            status = (400, {'success': False, 'error': 'Invalid input data.'})

        return status

    # used in APIMetaDataHandler [DELETE]
    def delete_slug(self, _id, user, slug_name):
        ''' 
            delete the slug of API _id. 
            UPDATED TO DSL
        '''
        if not self.exists(_id):
            return (404, {"success": False, "error": "Could not retrieve API '{}' to delete slug name".format(_id)})

        i = API_Doc.get(id=_id).to_dict()
        _user = i.get('_meta', {}).get('github_username', '')

        # Make sure this is the correct user
        if user.get('login', None) != _user:
            return (405, {"success": False, "error": "User '{}' is not the owner of API '{}'".format(user.get('login', None), _id)})

        # Make sure this is the correct slug name
        if self._doc.to_dict().get('_meta', {}).get('slug', '') != slug_name:
            return (405, {"success": False, "error": "API '{}' slug name is not '{}'".format(_id, slug_name)})

        self._doc.update(id=_id, refresh=True, _meta={"slug": ""})

        return (200, {"success": True, "{}".format(_id): "slug '{}' deleted".format(slug_name)})