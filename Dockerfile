#FROM nvidia/cuda:9.2-cudnn7-devel-ubuntu18.04
FROM nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04
#FROM nvidia/cuda:10.0-cudnn7-devel-ubuntu18.04

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

RUN pip3 install torch==1.7.1+cu101 torchvision==0.8.2+cu101 torchaudio==0.7.2 -f https://download.pytorch.org/whl/torch_stable.html

#RUN pip3 install \
#    torch==1.3.0+cu100 -f https://download.pytorch.org/whl/torch_stable.html

#WORKDIR /tmp/apex
#RUN git clone https://github.com/NVIDIA/apex.git && \
#    cd apex && \
#    pip3 install -v --no-cache-dir --global-option="--cpp_ext" --global-option="--cuda_ext" .


RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir \
    jupyter \
    tensorflow


WORKDIR /workspace
#COPY . transformers/
RUN git clone https://github.com/huggingface/transformers && \
    cd transformers/ && \
    python3 -m pip install --no-cache-dir .

RUN pip3 install datasets==1.4.1 && \
    pip3 install transformers==4.4.0 && \
    pip3 install soundfile && \
    pip3 install jiwer && \
    pip3 install librosa
CMD ["/bin/bash"]


###############################
###   TORCH, APEX TENSORRT  ###
###############################
#RUN pip3 install \
#    install torch==1.7.1+cu92 torchvision==0.8.2+cu92 torchaudio==0.7.2 -f https://download.pytorch.org/whl/torch_stable.html
