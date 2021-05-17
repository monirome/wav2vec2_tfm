FROM nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04


RUN apt update && \
    apt install -y bash \
                   build-essential \
                   git \
                   curl \
                   ca-certificates \
                   libsndfile1 \
                   python3 \
                   python3-pip && \
    rm -rf /var/lib/apt/lists

RUN apt update && \
    apt install -y language-pack-en && \
    locale-gen en_US.UTF-8

ENV LANG=en_US.utf8
ENV LC_ALL='en_US.utf8'

#RUN pip3 install torch==1.7.1+cu92 torchvision==0.8.2+cu92 torchaudio==0.7.2 -f https://download.pytorch.org/whl/torch_stable.html
#RUN pip3 install torch==1.6.0+cu101 torchvision==0.7.0+cu101 torchaudio==0.6.0 -f https://download.pytorch.org/whl/torch_stable.html

RUN pip3 install torch==1.7.1+cu101 torchvision==0.8.2+cu101 torchaudio==0.7.2 -f https://download.pytorch.org/whl/torch_stable.html

WORKDIR /workspace
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir \
    jupyter

RUN git clone https://github.com/huggingface/transformers.git && \
    cd transformers && \
    pip3 install -e .


RUN pip3 install datasets && \
    pip3 install soundfile && \
    pip3 install jiwer==2.2.0 && \
    pip3 install lang-trans==0.6.0 && \
    pip3 install librosa==0.8.0

WORKDIR /workspace/wav2vec2

CMD ["/bin/bash"]
