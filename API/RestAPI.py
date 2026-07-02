import pymongo
import netifaces as ni
import sys, getopt
import netifaces as ni
import re
from regex import R
from pprint import pprint
import json
import os
from flask import Flask,request
from bson.json_util import dumps
from flask_cors import CORS
from dict2xml import dict2xml
import generatorv2
import socketAPI
from flask import Response

POLICY_DIR = os.path.join(os.path.dirname(__file__), "LowLevelPolicy")


companies = [{"id":1, "name": "Company One"}, {"id": 2, "name": "Company Two"}]

api = Flask(__name__)
CORS(api)

@api.route('/url/get', methods = ['GET'])
def restGetURLGroup():
    query = request.json
    client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    db = client["endpoint"]
    col = db["url"]

    query = {query} #{"name":key}
    res = col.find_one(query)
    
    return json.loads(dumps(res))

@api.route('/url/put', methods = ['PUT'])
def restInsertURLGroup():
    try:
        data = request.json
        print(data)
        client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
        db = client["endpoint"]
        col = db["url"]
        
        res = col.insert_one(data)
        return "Success"
    except pymongo.errors.DuplicateKeyError:
        print("Duplicate Key for ",data["name"])

@api.route('/nsfDB/get', methods = ['GET'])
def restGetAllCapability(query={}):
    client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    db = client["nsfDB"]
    col = db["capabilities"]
    result = {}
    result["nsf"] = []
    for res in col.find(query):
        result["nsf"].append(res)
    return json.loads(dumps(result))

@api.route('/user/put', methods = ['PUT'])
def restInsertUserGroup():
    try:
        data = request.json
        client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
        db = client["endpoint"]
        col = db["user"]
        
        res = col.insert_one(data)
        return "Success"
    except pymongo.errors.DuplicateKeyError:
        return "Duplicate Key for ",data["name"]
        

@api.route('/user/get', methods = ['GET'])
def restGetUserGroup():
    
    client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    db = client["endpoint"]
    col = db["user"]
    query = request.json
    res = col.find_one(query)
    return res

@api.route('/location/put', methods = ['PUT'])
def restInsertLocationGroup():
    try:
        data = request.json
        client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
        db = client["endpoint"]
        col = db["location"]
        
        res = col.insert_one(data)
        return "Success"
    except pymongo.errors.DuplicateKeyError:
        print("Duplicate Key for ",data["name"])

@api.route('/location/get', methods = ['GET'])
def restGetLocationGroup():
    client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
    db = client["endpoint"]
    col = db["location"]
    query = request.json
    res = col.find_one(query)
    return res


# Insert Capabilities of an NSF. The DMS delivers the capabilities via Registration Interface
@api.route('/register/nsf', methods = ['PUT'])
def restInsertCapability():
    try:
        data = request.json
        client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
        db = client["nsfDB"]
        col = db["capabilities"]
        print(data)
        res = col.insert_one(data)
        return "Success"
    except pymongo.errors.DuplicateKeyError:
        print("Duplicate Key for ",data["nsf-name"])
        return Response(f"Duplicate Key for {data['nsf-name']}", status=400)


#API for security policy tranlator - Input High-level policy (CFI), Output Low-level policy (NFI)
#http://ipv4:5000/high_level
@api.route('/high_level', methods=['PUT'])
def restInsertConfiguration():
    req = request.json
    #start = datetime.datetime.now()
    data = cleanNullTerms(req)
    print(data)
    xml = dict2xml(data)
    result = generatorv2.gen(xml)
    #end = datetime.datetime.now()
    # time = end-start
    # result["time"] = time.total_seconds()
    # result["optimal"] = optimal.total_seconds()
    # for x,y in result.items():
    #     print(x)
    #     print(y)
    return result

# 다른 팀이 생성한 ROS2 .sh 파일을 받아서 LIMO에 실행
# POST body: {"command": "forward"}  → ros2_commands/forward.sh 실행
@api.route('/policy/deploy', methods=['POST'])
def deployPolicy():
    data = request.json
    if not data or 'command' not in data:
        return Response('{"error": "command 필드가 필요합니다 (예: \\"forward\\")"}',
                        status=400, mimetype='application/json')

    command = data['command']
    sh_path = socketAPI.get_ros2_file_path(command)

    # 다른 팀이 생성한 .sh 파일 내용을 요청에 포함한 경우 저장
    sh_content = data.get('sh_content', '')
    if sh_content:
        os.makedirs(os.path.dirname(sh_path), exist_ok=True)
        with open(sh_path, 'w', encoding='utf-8') as f:
            f.write(sh_content)
        print(f"[DEPLOY] ROS2 파일 저장: {sh_path}")

    success, message = socketAPI.execute_ros2_file(sh_path)
    if success:
        return Response(json.dumps({"status": "success", "command": command, "message": message}),
                        status=200, mimetype='application/json')
    else:
        return Response(json.dumps({"status": "failed", "command": command, "message": message}),
                        status=500, mimetype='application/json')

def cleanNullTerms(d):
   clean = {}
   for k, v in d.items():
      if isinstance(v, dict):
         nested = cleanNullTerms(v)
         if len(nested.keys()) > 0:
            clean[k] = nested
      elif v is not None:
         clean[k] = v
   return clean

def main(argv):
#  print(sys.argv[1])
  ip = ''
  opts, args = getopt.getopt(argv,"h",["ip=","if="])
  for opt, arg in opts:
    if opt == '-h':
      print("RestAPI.py [--ip <ip-address>|--if <interface-name>]")
      sys.exit()
    elif opt in ("--ip"):
      if re.match("^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$",arg):
        ip = arg
      else:
        print(f"{arg} is not a valid IP address")
        sys.exit()
    elif opt in ("--if"):
      try:
        ip = ni.ifaddresses(arg)[ni.AF_INET][0]['addr']
      except ValueError:
        print(f"Invalid interface value. The value must be: {ni.interfaces()}")
        sys.exit()
  if ip == '':
    ip = '127.0.0.1'
    print(f"IP 미지정 → 기본값 {ip}:5000 으로 실행")
  api.run(host=ip, port=5000)

if __name__== '__main__':
  main(sys.argv[1:])
