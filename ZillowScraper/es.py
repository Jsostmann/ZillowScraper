from datetime import datetime
from elasticsearch import Elasticsearch
#from elasticsearch5 import Elasticsearch
import json

es = Elasticsearch("http://localhost:9200")
data = open("data/11_08_2022_11:42_Greensboro_NC.json", 'r')
d = json.loads(data.read())


new_mapping = {
    "mappings":{
         "dynamic": "strict",
         "properties":{
            "latLong": {
               "properties": {
                  "latitude":{
                     "type": "text"
                  },
                  "longitude": {
                     "type": "text"
                  }
               }
            },
            "latitude": {
               "type": "text"
            },
            "longitude": {
               "type": "text"
            },
            "address":{
               "type":"text"
            },
            "baths":{
               "type":"float"
            },
            "beds":{
               "type":"long"
            },
            "city":{
               "type":"text"
            },
            "detailUrl":{
               "type":"text"
            },
            "homeType":{
               "type":"text"
            },
            "loc":{
                "type": "geo_point"
            },
            "price":{
               "type":"text"
            },
            "state":{
               "type":"text"
            },
            "zipcode":{
               "type":"text"
            }
         }
    }
}
#print(es.indices.put_mapping(index="listings", body=new_mapping))
#print(es.indices.get_mapping(index="listings"))

#exit()


if es.indices.exists(index="listings"):
    es.indices.delete(index="listings")

if not es.indices.exists(index="listings"):
    es.indices.create(index="listings", body=new_mapping)
es.indices.refresh(index="listings")

for listing in d["listings"]:
    resp = es.index(index="listings", body=d['listings'][listing])
es.indices.refresh(index="listings")

#resp = es.get(index="listings", id=1)
#print(resp['_source'])

es.indices.refresh(index="listings")
'''
resp = ces.search(index="test-index", query={"match_all": {}})
print("Got %d Hits:" % resp['hits']['total']['value'])
for hit in resp['hits']['hits']:
    print("%(timestamp)s %(author)s: %(text)s" % hit["_source"])
    '''