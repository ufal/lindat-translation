models_resource_links_example = {
        "item": [
            {
                "href": "/api/v2/models/en-cs",
                "name": "en-cs",
                "title": "en-cs (English->Czech (CUBBITT))"
            },
            {
                "href": "/api/v2/models/cs-en",
                "name": "cs-en",
                "title": "cs-en (Czech->English (CUBBITT))"
            }
        ],
        "self": {
            "href": "/api/v2/models/"
        }
}
models_resource_embedded_example = {
        "item": [
            {
                "_links": {
                    "self": {
                        "href": "/api/v2/models/en-cs"
                    },
                    "translate": {
                        "href": "/api/v2/models/en-cs{?src,tgt}",
                        "templated": True
                    }
                },
                "default": True,
                "domain": "",
                "model": "en-cs",
                "supports": {
                    "en": [
                        "cs"
                    ]
                },
                "title": "en-cs (English->Czech (CUBBITT))"
            },
            {
                "_links": {
                    "self": {
                        "href": "/api/v2/models/cs-en"
                    },
                    "translate": {
                        "href": "/api/v2/models/cs-en{?src,tgt}",
                        "templated": True
                    }
                },
                "default": False,
                "domain": "",
                "model": "cs-en",
                "supports": {
                    "cs": [
                        "en"
                    ]
                },
                "title": "cs-en (Czech->English (CUBBITT))"
            }
        ]
}
