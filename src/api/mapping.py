smart_api_mapping = {
    "_doc": {
        "dynamic_templates": [
            {
                "ignore_example_field": {
                    "match": "example",
                    "mapping": {
                        "index": False,
                        "type": "text"
                    }
                }
            },
            {
                "ignore_ref_field": {
                    "match": "$ref",
                    "mapping": {
                        "index": False
                    }
                }
            },
            {
                "ignore_schema_field": {
                    "match": "schema",
                    "mapping": {
                        "enabled": False
                    }
                }
            },
            {
                "ignore_content_field": {
                    "match": "content",
                    "mapping": {
                        "enabled": False
                    }
                }
            },
            # this is the last template
            # strings are indexed as both texts and keywords
            {
                "strings": {
                    "match_mapping_type": "string",
                    "mapping": {
                        "type": "text",
                        "index": True,
                        "ignore_malformed": True,
                        "fields": {
                            "raw": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    }
                }
            }
        ],
        "properties": {
            "components": {
                "enabled": False
            },
            "definitions": {
                "enabled": False
            },
            "~raw": {
                "type": "binary"
            }
        }
    }
}
