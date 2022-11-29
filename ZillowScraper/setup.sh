#!/bin/bash

elasticsearch_version="7.17.7"
kibana_version="7.17.7"
network_name="elasticsearch-kibana"
elastic_container_name="elasticsearch"
kibana_container_name="kibana"
es_username="elastic"
es_password="password"


elasticsearch_installed=$(docker images --filter reference="docker.elastic.co/elasticsearch/elasticsearch:$elasticsearch_version")
kibana_installed=$(docker images --filter reference="docker.elastic.co/kibana/kibana:$kibana_version")



function install_elasticsearch() {
    #r=$(docker run --name $elastic_container_name --network $network_name --publish 9200:9200 --publish 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled: true" docker.elastic.co/elasticsearch/elasticsearch:$elasticsearch_version 2>&1>/dev/null)
    r=$(docker run --name $elastic_container_name --network $network_name --publish 9200:9200 --publish 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=true" -e "ELASTIC_USERNAME=$es_username" -e "ELASTIC_PASSWORD=$es_password" docker.elastic.co/elasticsearch/elasticsearch:$elasticsearch_version 2>&1>/dev/null)
    [ -n "$r" ] && echo 1 || echo 0
}
function install_kibana() {
    #r=$(docker run --name $kibana_container_name --publish 5601:5601 --network $network_name -e "ELASTICSEARCH_URL=http://elasticsearch:9200" -e "elasticsearch.username: kibana_system" kibana:$kibana_version 2>&1>/dev/null)
    r=$(docker run --name $kibana_container_name --publish 5601:5601 --network $network_name -e "ELASTICSEARCH_URL=http://elasticsearch:9200" -e "ELASTICSEARCH_USERNAME=$es_username" -e "ELASTICSEARCH_PASSWORD=$es_password" -e "xpack.security.enabled=true" docker.elastic.co/kibana/kibana:$kibana_version 2>&1>/dev/null)
    [ -n "$r" ] && echo 1 || echo 0
}

function check_for_network() {
    network_created=$(docker network ls | grep -w $network_name)

    if [ -z "$network_created" ]; then
        echo "No docker network found, creating now..."
        docker network create elastic 1>/dev/null
        [ $? -eq 0 ] && echo 0 || echo 1 
    else
        echo "Docker network found"
    fi
}

function check_for_images() {
    if [ -z "$elasticsearch_installed" ]; then
        echo "ElasticSearch image not found installing now..."

        [ $(install_elasticsearch) == 1 ] && echo "Failed to install elasticsearch image..."
        exit 1
    else
        echo "ElasicSearch Image Found"
    fi  


    if [ -z "$kibana_installed" ]; then
        echo "Kibana image not found installing now..."
        [ $(install_kibana) == 1 ] && echo "Failed to install kibana image..."
        exit 1
    else
        echo "Kibana image Found"
    fi
}


check_for_network
check_for_images





