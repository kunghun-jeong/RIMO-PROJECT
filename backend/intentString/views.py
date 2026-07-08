import paramiko
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import NaturalIntentSerializer, NetworkIntentSerializer, ApplicationIntentSerializer, PolicyIntentSerializer
from .models import NaturalIntent, NetworkIntent, ApplicationIntent, PolicyIntent
from .services.intentToPolicy import map_intent_struct_to_policy, generate_yaml
from .services.connection import action_to_cmd_vel, send_to_limo, send_sequence_to_limo, run as limo_run
from .services.limo_llm import natural_to_limo_command, natural_to_limo_sequence
from .services import yolo_avoid
import requests
import json
from django.conf import settings
import yaml
import os


# Create your views here.
def test(request):
      return HttpResponse("Test")

# 파일 저장 수행하는 함수
def safe_write_txt(filename, content):
    try:
        save_dir = os.path.join(settings.BASE_DIR, "intent_logs")
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[LOG SAVED] {file_path}")

    except Exception as e:
        print("File save skipped:", e)


#  공통: DB 없는 환경에서도 정상 작동하도록 하는 Safe Save 함수
def safe_save(serializer):
    try:
        return serializer.save()
    except Exception as e:
        print("DB save skipped:", e)
        return None

def safe_create(model, **kwargs):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(LIMO_HOST, username=LIMO_USER, password=LIMO_PASS, timeout=10)
        _, stdout, stderr = ssh.exec_command(f'bash -c "{ROS2_CMD}"', timeout=35)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        ssh.close()
        print(f"[LIMO] exit={exit_code} out={out[:200]} err={err[:200]}")
        return {"status": "success" if exit_code == 0 else "failed",
                "exit": exit_code, "out": out, "err": err}
    except Exception as e:
        print(f"[LIMO] SSH 오류: {e}")
        return {"status": "failed", "error": str(e)}


class NaturalIntentViewSet(viewsets.ModelViewSet):
    queryset = NaturalIntent.objects.all()
    serializer_class = NaturalIntentSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        intent_obj = safe_save(serializer)

        payload = serializer.data

        external_url = "http://115.145.179.159:5050/infer"
        print("\n===== [DEBUG] Sending payload to external server =====")
        print(f"URL: {external_url}")
        print(f"Payload: {payload}")
        print("=======================================================\n")

        try:
            response = requests.post(external_url, json=payload, timeout=30)
            external_response = json.loads(response.text)

            intent = external_response.get("Intent", {})
            triple = external_response.get("KGTriple", {})
            confidence = external_response.get("confidence", 1.0)

            policy = map_intent_struct_to_policy(intent, triple, confidence)
            yaml_result = generate_yaml(policy)

            safe_write_txt(
                "policy_external.txt",
                json.dumps(external_response, indent=4, ensure_ascii=False)
            )
            safe_write_txt(
                "policy_yaml.txt",
                yaml_result
            )

            yaml_path = os.path.join(settings.BASE_DIR, "intent_logs", "policy_yaml.txt")
            limo_run(yaml_path)

            safe_create(
                PolicyIntent,
                action=intent.get("Action", ""),
                expectation_object=intent.get("ExpectationObject", ""),
                expectation_target=intent.get("ExpectationTarget", ""),
                head=triple.get("head", ""),
                relation=triple.get("relation", ""),
                tail=triple.get("tail", ""),
            )

        except Exception as e:
            external_response = f"Failed to send: {e}"

        return Response({
            "saved": serializer.data,
            "sent_to": external_url,
            "external_payload": payload,
            "external_response": external_response,
        }, status=status.HTTP_201_CREATED)


class NetworkIntentViewSet(viewsets.ModelViewSet):
    queryset = NetworkIntent.objects.all()
    serializer_class = NetworkIntentSerializer

    def create(self, request, *args, **kwargs):

        data = request.data.get('intent')
        obj = {
            "name": data['name'],
            "mac_address": data['mac-address'],
            "ipv4_start": data['range-ipv4-address']['start'],
            "ipv4_end": data['range-ipv4-address']['end'],
            "ipv6_start": data['range-ipv6-address']['start'],
            "ipv6_end": data['range-ipv6-address']['end'],
        }

        serializer = self.get_serializer(data=obj)
        serializer.is_valid(raise_exception=True)

        intent_obj = safe_save(serializer)

        payload = {"intent": serializer.data}
        external_url = "http://115.145.179.159:5050/infer"

        print("\n===== [DEBUG] Sending payload to external server =====")
        print(f"URL: {external_url}")
        print(f"Payload: {payload}")
        print("=======================================================\n")

        try:
            response = requests.post(external_url, json=payload, timeout=30)
            external_response = json.loads(response.text)
        except Exception as e:
            external_response = f"Failed to send: {e}"

        return Response({
            "saved": serializer.data,
            "sent_to": external_url,
            "external_payload": payload,
            "external_response": external_response,
        }, status=status.HTTP_201_CREATED)


class ApplicationIntentViewSet(viewsets.ModelViewSet):
    queryset = NetworkIntent.objects.all()
    serializer_class = ApplicationIntentSerializer

    def create(self, request, *args, **kwargs):

        data = request.data
        obj = {
            "user_label": data.get("user_label", ""),
            "expectation_id": data.get("expectation_id", ""),
            "expectation_verb": data.get("expectation_verb", ""),
            "object_type": data.get("object_type", ""),

            "context_attribute" : data["context_attributes"][0].get("contextAttribute", ""),
            "context_condition" : data["context_attributes"][0].get("contextCondition", ""),
            "context_targer_id" : data["context_attributes"][0].get("contextValueRange", ""),

            "target_name" : data["target_metrics"][0].get("targetName",""),
            "target_condition" : data["target_metrics"][0].get("targetCondition",""),
            "target_value" : data["target_metrics"][0].get("targetValueRange",""),

            "priority": data.get("priority", ""),
            "location": data.get("location", ""),
            "observation_period": data.get("observation_period", ""),
            "report_reference": data.get("report_reference", ""),
        }

        serializer = self.get_serializer(data=obj)
        serializer.is_valid(raise_exception=True)

        intent_obj = safe_save(serializer)

        payload = {"intent": serializer.data}
        external_url = "http://115.145.179.159:5050/infer"

        print("\n===== [DEBUG] Sending payload to external server =====")
        print(f"URL: {external_url}")
        print(f"Payload: {payload}")
        print("=======================================================\n")

        try:
            response = requests.post(external_url, json=payload, timeout=30)
            external_response = json.loads(response.text)
        except Exception as e:
            external_response = f"Failed to send: {e}"

        print("\n===== [DEBUG] External Response =====")
        print(f"External Response: {external_response}")
        print("=======================================================\n")

        return Response({
            "saved": serializer.data,
            "sent_to": external_url,
            "external_payload": payload,
            "external_response": external_response,
        }, status=status.HTTP_201_CREATED)


class LimoDirectView(APIView):
    def post(self, request):
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"error": "text field required"}, status=status.HTTP_400_BAD_REQUEST)

        sequence = natural_to_limo_sequence(text)

        step_results = send_sequence_to_limo(sequence)
        all_success = all(r["success"] for r in step_results)

        results = []
        for step, result in zip(sequence, step_results):
            results.append({
                "command":  step["command"],
                "speed":    step["speed"],
                "duration": step["duration"],
                "cmd_vel":  action_to_cmd_vel(step["command"]),
                "success":  result["success"],
            })

        from django.utils import timezone
        safe_create(NaturalIntent, user="limo_direct", intent=text[:50], timestamp=timezone.now())

        return Response({
            "input":        text,
            "sequence":     results,
            "limo_success": all_success,
        }, status=status.HTTP_200_OK)


class LimoYoloView(APIView):
    def post(self, request):
        action = request.data.get("action", "")
        if action == "start":
            yolo_avoid.start()
            return Response({"status": "started"})
        elif action == "stop":
            yolo_avoid.stop()
            return Response({"status": "stopped"})
        elif action == "tick":
            result = yolo_avoid.tick()
            return Response(result)
        return Response({"error": "action must be start, stop or tick"}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        return Response(yolo_avoid.get_status())
