import os

import json
import pytest

from web.api.controller import APIDocController, SlugRegistrationError, get_api_metadata_by_url

class TestController:

    # my_gene
    # _doc_id = 'f307760715d91908d0ae6de7f0810b22'

    _my_gene_id = ''

    _my_disease_id = ''

    # my_disease
    # _doc_id_two = '59dce17363dce279d389100834e43648'

    _test_slug = 'myslug'

    _user = {"login": "marcodarko"}

    _my_gene = {}

    _my_disease = {}

    _my_gene_url = 'https://raw.githubusercontent.com/NCATS-Tangerine/translator-api-registry/master/mygene.info/openapi_full.yml'

    _my_disease_url = 'https://raw.githubusercontent.com/NCATS-Tangerine/translator-api-registry/master/mydisease.info/smartapi.yaml'

    @classmethod
    def setup_class(cls):
        """ 
        Model is given an already transformed doc with an already encoded ID 
        and _meta field with test user
        """
        cls._my_gene = get_api_metadata_by_url(cls._my_gene_url)

        cls._my_disease = get_api_metadata_by_url(cls._my_disease_url)

        # with open(os.path.join(os.path.dirname(__file__), "data/mygene.json")) as f:
        #     cls.my_gene = json.load(f)

        # with open(os.path.join(os.path.dirname(__file__), "data/mydisease.json")) as f:
        #     cls.my_disease = json.load(f)

    def test_add_doc_1(self):
        """
        Add test My Gene API to index, return new doc ID
        """
        res = APIDocController.add(self.my_gene,
                                   user_name=self._user['login'],
                                   url=self._my_gene_url)

        self._my_gene_id = res.get('_id', None)

        assert isinstance(self._my_gene_id, str)

    def test_add_doc_2(self):
        """
        Add test My Disease API to index, return new doc ID
        """
        res = APIDocController.add(self.my_disease,
                                   user_name=self._user['login'],
                                   url=self._my_disease_url)

        self._my_disease_id = res.get('_id', None)

        assert isinstance(self._my_disease_id, str)

    def test_get_all(self):
        """
        Get ALL docs
        """
        docs = APIDocController.get_all()
        assert isinstance(docs, list)

    def test_get_one(self):
        """
        Get one doc by ID
        """
        _id = self._my_gene_id

        doc = APIDocController.get_api(api_name=_id)
        assert isinstance(doc, dict)

    def test__get_tags(self):
        """
        Get tag aggregations for field
        """
        field = 'info.contact.name'
        size = 100

        res = APIDocController.get_tags(field=field, size=size)
        assert len(res.get('aggregations', {}).get('field_values', {}).get('buckets', [])) >= 1 

    def test_validate_slug(self):
        """
        Update registered slug name for ID
        """
        slug = self._test_slug
        APIDocController.validate_slug_name(slug_name=slug)
        assert True

    def test_validate_slug_invalid(self):
        """
        Update registered slug name for ID
        """
        invalid_slug = 'smart-api'
        with pytest.raises(SlugRegistrationError):
            APIDocController.validate_slug_name(slug_name=invalid_slug)
        
        # try:
        #     APIDocController.validate_slug_name(slug_name=invalid_slug)
        # except SlugRegistrationError:
        #     pass
        # else:
        #     assert False

    def test_update_slug(self):
        """
        Update registered slug name for ID
        """
        api_id = self._my_gene_id
        slug = self._test_slug
        user = self._user

        doc = APIDocController(api_id)
        res = doc.update_slug(_id=api_id, user=user, slug_name=slug)
        assert res.get(f'{api_id}._meta.slug', False) == slug

    def test__get_api_from_slug(self):
        """
        Get ID of doc with slug
        """
        slug = self._test_slug

        _id = APIDocController.get_api_id_from_slug(slug=slug)
        assert isinstance(_id, str)

    def test_model_slug_taken(self):
        """
        Slug name already exists
        """
        APIDocController.slug_is_available(slug=self._test_slug)

    def test_delete_slug(self):
        """
        Delete slug for ID
        """
        api_id = self._my_gene_id
        slug = self._test_slug
        user = self._user

        doc = APIDocController(api_id)
        res = doc.delete_slug(_id=api_id, user=user, slug_name=slug)
        assert res == f"slug '{slug}' for {api_id} was deleted"

    def test_refresh_api(self):
        """
        Refresh single api with id
        """
        api_id = self._my_gene_id
        user = self._user

        doc = APIDocController(api_id)
        res = doc.refresh_api(_id=api_id, user=user, test=True)
        assert res.get('test-updated', '') == f"API with ID {api_id} was refreshed"

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup.
        """
        print("teardown")
        # TODO make sure its deleted 