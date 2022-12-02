#!/bin/bash

elasticsearch_version="7.17.7"
kibana_version="7.17.7"
network_name="elasticsearch-kibana"
elastic_container_name="elasticsearch"
kibana_container_name="kibana"
es_username="elastic"
es_password="password"


elasticsearch_installed=$((docker images --filter reference=$elastic_container_name:$elasticsearch_version | grep $elasticsearch_version) 2>/dev/null)
kibana_installed=$((docker images --filter reference=$kibana_container_name:$kibana_version | grep $kibana_version) 2>/dev/null)
elasticsearch_created=$((docker ps -a --filter name=$elastic_container_name | grep $elastic_container_name) 2>/dev/null)
kibana_created=$((docker ps -a --filter name=$kibana_container_name | grep $kibana_container_name) 2>/dev/null)

function check_exit_status() {
    [ $? -ne 0 ] && exit 1
}

function check_docker_running() {
    docker ps 1>/dev/null 2>&1
    if [ $? -eq 1 ]; then
        echo "Docker is not running please start"
        exit 1
    fi
}

function build_elasticsearch() {
    r=$(docker run -d --name $elastic_container_name --network $network_name --publish 9200:9200 --publish 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=true" -e "ELASTIC_USERNAME=$es_username" -e "ELASTIC_PASSWORD=$es_password" elasticsearch:$elasticsearch_version 2>&1>/dev/null)
    [ -z "$r" ] && echo 0 || echo 1
}

function build_kibana() {
    r=$(docker run -d --name $kibana_container_name --publish 5601:5601 --network $network_name -e "ELASTICSEARCH_URL=http://elasticsearch:9200" -e "ELASTICSEARCH_USERNAME=$es_username" -e "ELASTICSEARCH_PASSWORD=$es_password" -e "xpack.security.enabled=true" kibana:$kibana_version 2>&1>/dev/null)
    [ -z "$r" ] && echo 0 || echo 1
}

function check_for_network() {
    network_created=$(docker network ls | grep -w $network_name)

    if [ -z "$network_created" ]; then
        echo "No docker network found, creating now..."
        docker network create "$network_name" 2>&1>/dev/null
        check_exit_status
    else
        echo "Docker network found"
    fi
}

function check_for_images() {
    if [ -z "$elasticsearch_installed" ]; then
        echo "ElasticSearch image not found pulling now..."
        docker pull $elastic_container_name:$elasticsearch_version 2>&1>/dev/null
        check_exit_status

        if [ $(build_elasticsearch) == 1 ]; then
            echo "Failed to build elasticsearch container..."
            exit 1
        fi
    else
        echo "ElasicSearch Image Found"
        if [ -z "$elasticsearch_created" ]; then
            build_elasticsearch 1>/dev/null
        else
            echo "Starting Elasticsearch container"
            docker start $elastic_container_name 2>&1>/dev/null
            check_exit_status
        fi
    fi  


    if [ -z "$kibana_installed" ]; then
        echo "Kibana image not found installing now..."
        docker pull $kibana_container_name:$kibana_version 2>&1>/dev/null
        check_exit_status

        if [ $(build_kibana) == 1 ]; then 
            echo "Failed to build kibana image..."
            exit 1
        fi
    else
        echo "Kibana image Found"
        if [ -z "$kibana_created" ]; then
            build_kibana 1>/dev/null
        else
            echo "Starting Kibana container"
            docker start $kibana_container_name 2>&1>/dev/null
            check_exit_status
        fi
    fi
}

check_docker_running
check_for_network
check_for_images