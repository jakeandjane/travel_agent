1.
用vllm跑通大模型：
python -m vllm.entrypoints.openai.api_server \
  --model /home/tyy/.cache/modelscope/hub/models/Qwen/Qwen1___5-1___8B-Chat \
  --served-model-name qwen-1.8b \
  --host 0.0.0.0 \
  --port 8001 \
  --dtype float16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.8 \
  --max-num-seqs 1 \
  --max-num-batched-tokens 512 \
  --trust-remote-code

2.
前端UI界面跑起来，npm run dev

3.
后端跑起来，直接运行run.py


