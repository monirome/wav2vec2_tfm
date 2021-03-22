# DOCKER BUILD
First build docker
```bash
sudo docker build -t  wav2vec2hf .
```


Create container:
```bash
sudo NV_GPU='5' nvidia-docker run -it -d --rm --name "wav2vec2hf_5" --runtime=nvidia --shm-size=4g --ulimit memlock=-1 --ulimit stack=67108864 -v $PWD:/workspace/wav2vec2/ -v /data/:/data/:ro wav2vec2hf
```


Execute container:
```bash
sudo nvidia-docker exec -it wav2vec2hf_5 bash
```

Go to the folder and simply execute:
```bash
python3 ExampleFinuting
```


