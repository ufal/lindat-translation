from app.main.api_examples.language_resource_example import language_resource_links_example

languages_resource_links_example = {
    "item": [
      {
        "href": "/api/v2/languages/cs",
        "name": "cs",
        "title": "Czech"
      }
    ],
    "self": {
      "href": "/api/v2/languages/"
    },
    "translate": {
      "href": "/api/v2/languages{?src,tgt}",
      "templated": True
    }
}

languages_resource_embedded_example = {
    "item": [
      {
        "_links": language_resource_links_example,
        "name": "cs",
        "title": "Czech"
      }
    ]
}
