from datasets import load_dataset, load_metric
import random
import pandas as pd
import re
import numpy as np
import json
import logging
from transformers.trainer_utils import get_last_checkpoint, is_main_process
import transformers
from transformers import (
    HfArgumentParser,
    Trainer,
    TrainingArguments,
    Wav2Vec2CTCTokenizer,
    Wav2Vec2FeatureExtractor,
    Wav2Vec2ForCTC,
    Wav2Vec2Processor,
    is_apex_available,
    set_seed,
)
import sys
transformers.logging.set_verbosity_info()
logger = logging.getLogger(__name__)


##########################################################################33
training_args = TrainingArguments(
    # output_dir="/content/gdrive/MyDrive/wav2vec2-large-xlsr-turkish-demo",
    output_dir="./wav2vec2-large-xlsr-PRUEBA-APHASIA",
    group_by_length=True,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=1,
    evaluation_strategy="steps",
    num_train_epochs=30,
    fp16=True,
    save_steps=500,
    eval_steps=500,
    logging_steps=500,
    learning_rate=0.0004,
    warmup_steps=500,
    save_total_limit=3,
    do_train=True,
    do_eval=True
)
##################################33

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s -   %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    )
logger.setLevel(logging.INFO if is_main_process(training_args.local_rank) else logging.WARN)

# Log on each process the small summary:
logger.warning(
    f"Process rank: {training_args.local_rank}, device: {training_args.device}, n_gpu: {training_args.n_gpu}"
    + f"distributed training: {bool(training_args.local_rank != -1)}, 16-bits training: {training_args.fp16}"
)
# Set the verbosity to info of the Transformers logger (on main process only):
if is_main_process(training_args.local_rank):
    transformers.utils.logging.set_verbosity_info()
logger.info("Training/evaluation parameters %s", training_args)

# Set seed before initializing model.
set_seed(training_args.seed)


###########################################################################################################################################
num_file_train=1000
num_file_eval=200

df = pd.read_csv("df_final.csv", delimiter=',')

dummy_dataset = []
for item in df.iterrows():
    dummy_dataset.append({"file": "/data/APHASIA/audios/"+item[1]["file_cut"],
                          "transcription": f"{item[1]['transcription']}"})

for i, sample in enumerate(dummy_dataset):
    with open(f'jsons/sample_{i}.json', 'w') as outfile:
        json.dump(sample, outfile)


###########################################################################################################################################
# def show_random_elements(dataset, num_examples=2):  # m_examples=10
#     assert num_examples <= len(dataset), "Can't pick more elements than there are in the dataset."
#     picks = []
#     for _ in range(num_examples):
#         pick = random.randint(0, len(dataset) - 1)
#         while pick in picks:
#             pick = random.randint(0, len(dataset) - 1)
#         picks.append(pick)
#     df = pd.DataFrame(dataset[picks])
#     print(df)

#def remove_special_characters(batch):
#    batch["sentence"] = re.sub(chars_to_ignore_regex, '', batch["sentence"]).lower() + " "
#    return batch

###########################################################################################
# Download some data to finetuning. In this case it is downloaded turkish from common voice
# common_voice_train = load_dataset("common_voice", "en", split="train")
# common_voice_test = load_dataset("common_voice", "en", split="test")

###########################################################################################################################################
common_voice_train = load_dataset("json", data_files=[f"jsons/sample_{i}.json" for i in range(num_file_train)], split="train")
common_voice_test = load_dataset("json", data_files=[f"jsons/sample_{i}.json" for i in range(num_file_train, num_file_train+num_file_eval)], split="train")

common_voice_train = common_voice_train.rename_column("file", "path")
common_voice_train = common_voice_train.rename_column("transcription", "sentence")

common_voice_test = common_voice_test.rename_column("file", "path")
common_voice_test = common_voice_test.rename_column("transcription", "sentence")

###########################################################################################################################################
#show_random_elements(common_voice_train.remove_columns(["path"]),5)

##################################################
# Normalize text ###############################
# chars_to_ignore_regex = '[\,\?\.\!\-\;\:\"\“\%\‘\”\�]'
# common_voice_train = common_voice_train.map(remove_special_characters, remove_columns=["age"])
# common_voice_test = common_voice_test.map(remove_special_characters, remove_columns=["age"])
#show_random_elements(common_voice_train.remove_columns(["path"]), 5)


####################################################
# Extract Vocabulary ###############################
def extract_all_chars(batch):
    all_text = " ".join(batch["sentence"])
    vocab = list(set(all_text))
    return {"vocab": [vocab], "all_text": [all_text]}


vocab_train = common_voice_train.map(extract_all_chars, batched=True, batch_size=-1, keep_in_memory=True,
                                     remove_columns=common_voice_train.column_names)
vocab_test = common_voice_test.map(extract_all_chars, batched=True, batch_size=-1, keep_in_memory=True,
                                   remove_columns=common_voice_test.column_names)
vocab_list = list(set(vocab_train["vocab"][0]) | set(vocab_test["vocab"][0]))
vocab_dict = {v: k for k, v in enumerate(vocab_list)}
vocab_dict["|"] = vocab_dict[" "]
del vocab_dict[" "]

vocab_dict["[UNK]"] = len(vocab_dict)
vocab_dict["[PAD]"] = len(vocab_dict)
print(len(vocab_dict))


with open('vocab.json', 'w') as vocab_file:
    json.dump(vocab_dict, vocab_file)

#################################################################
# PREPARE FINETUNE ######################################################
from transformers import Wav2Vec2CTCTokenizer, Wav2Vec2FeatureExtractor, Wav2Vec2Processor

tokenizer = Wav2Vec2CTCTokenizer("./vocab.json", unk_token="[UNK]", pad_token="[PAD]", word_delimiter_token="|")
feature_extractor = Wav2Vec2FeatureExtractor(feature_size=1, sampling_rate=16000, padding_value=0.0, do_normalize=True,
                                             return_attention_mask=True)
processor = Wav2Vec2Processor(feature_extractor=feature_extractor, tokenizer=tokenizer)

#print(common_voice_train[0])

#################################################################
# PREPARE AUDIOS ######################################################
import torchaudio

def speech_file_to_array_fn(batch):
    speech_array, sampling_rate = torchaudio.load(batch["path"])
    batch["speech"] = speech_array[0].numpy()
    batch["sampling_rate"] = sampling_rate
    batch["target_text"] = batch["sentence"]
    return batch

common_voice_train = common_voice_train.map(speech_file_to_array_fn, remove_columns=common_voice_train.column_names)
common_voice_test = common_voice_test.map(speech_file_to_array_fn, remove_columns=common_voice_test.column_names)

########################################
# DOWNSAMPLE DATA #####################
# import librosa
# import numpy as np

# def resample(batch):
#     batch["speech"] = librosa.resample(np.asarray(batch["speech"]), 48_000, 16_000)
#     batch["sampling_rate"] = 16_000
#     return batch

# common_voice_train = common_voice_train.map(resample, num_proc=2) # num_proc=10
# common_voice_test = common_voice_test.map(resample, num_proc=2) # num_proc=10


##############################################
# Prepare data for training ##################
def prepare_dataset(batch):
    # check that all files have the correct sampling rate
    assert (
        len(set(batch["sampling_rate"])) == 1
    ), f"Make sure all inputs have the same sampling rate of {processor.feature_extractor.sampling_rate}."
    batch["input_values"] = processor(batch["speech"], sampling_rate=batch["sampling_rate"][0]).input_values
    with processor.as_target_processor():
        batch["labels"] = processor(batch["target_text"]).input_ids
    return batch

common_voice_train = common_voice_train.map(prepare_dataset, remove_columns=common_voice_train.column_names, batch_size=10, num_proc=20, batched=True)
common_voice_test = common_voice_test.map(prepare_dataset, remove_columns=common_voice_test.column_names, batch_size=10, num_proc=20, batched=True)


###################################################
# Training ########################################

import torch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class DataCollatorCTCWithPadding:
    """
    Data collator that will dynamically pad the inputs received.
    Args:
        processor (:class:`~transformers.Wav2Vec2Processor`)
            The processor used for proccessing the data.
        padding (:obj:`bool`, :obj:`str` or :class:`~transformers.tokenization_utils_base.PaddingStrategy`, `optional`, defaults to :obj:`True`):
            Select a strategy to pad the returned sequences (according to the model's padding side and padding index)
            among:
            * :obj:`True` or :obj:`'longest'`: Pad to the longest sequence in the batch (or no padding if only a single
              sequence if provided).
            * :obj:`'max_length'`: Pad to a maximum length specified with the argument :obj:`max_length` or to the
              maximum acceptable input length for the model if that argument is not provided.
            * :obj:`False` or :obj:`'do_not_pad'` (default): No padding (i.e., can output a batch with sequences of
              different lengths).
        max_length (:obj:`int`, `optional`):
            Maximum length of the ``input_values`` of the returned list and optionally padding length (see above).
        max_length_labels (:obj:`int`, `optional`):
            Maximum length of the ``labels`` returned list and optionally padding length (see above).
        pad_to_multiple_of (:obj:`int`, `optional`):
            If set will pad the sequence to a multiple of the provided value.
            This is especially useful to enable the use of Tensor Cores on NVIDIA hardware with compute capability >=
            7.5 (Volta).
    """
    processor: Wav2Vec2Processor
    padding: Union[bool, str] = True
    max_length: Optional[int] = None
    max_length_labels: Optional[int] = None
    pad_to_multiple_of: Optional[int] = None
    pad_to_multiple_of_labels: Optional[int] = None

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        # split inputs and labels since they have to be of different lenghts and need
        # different padding methods
        input_features = [{"input_values": feature["input_values"]} for feature in features]
        label_features = [{"input_ids": feature["labels"]} for feature in features]
        batch = self.processor.pad(
            input_features,
            padding=self.padding,
            max_length=self.max_length,
            pad_to_multiple_of=self.pad_to_multiple_of,
            return_tensors="pt",
        )
        with self.processor.as_target_processor():
            labels_batch = self.processor.pad(
                label_features,
                padding=self.padding,
                max_length=self.max_length_labels,
                pad_to_multiple_of=self.pad_to_multiple_of_labels,
                return_tensors="pt",
            )
        # replace padding with -100 to ignore loss correctly
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        batch["labels"] = labels
        return batch


data_collator = DataCollatorCTCWithPadding(processor=processor, padding=True)
wer_metric = load_metric("wer")

def compute_metrics(pred):
    pred_logits = pred.predictions
    pred_ids = np.argmax(pred_logits, axis=-1)
    pred.label_ids[pred.label_ids == -100] = processor.tokenizer.pad_token_id
    pred_str = processor.batch_decode(pred_ids)
    # we do not want to group tokens when computing the metrics
    label_str = processor.batch_decode(pred.label_ids, group_tokens=False)
    wer = wer_metric.compute(predictions=pred_str, references=label_str)
    return {"wer": wer}


from transformers import Wav2Vec2ForCTC, TrainingArguments, Trainer

model = Wav2Vec2ForCTC.from_pretrained(
    "facebook/wav2vec2-large-xlsr-53",
    activation_dropout=0.07,
    attention_dropout=0.2,
    hidden_dropout=0.04,
    feat_proj_dropout=0.2,
    mask_time_prob=0.1,
    layerdrop=0.05,
    gradient_checkpointing=True,
    ctc_loss_reduction="mean",
    pad_token_id=processor.tokenizer.pad_token_id,
    vocab_size=len(processor.tokenizer)
)

model.freeze_feature_extractor()

trainer = Trainer(
    model=model,
    data_collator=data_collator,
    args=training_args,
    compute_metrics=compute_metrics,
    train_dataset=common_voice_train,
    eval_dataset=common_voice_test,
    tokenizer=processor.feature_extractor,
)

if training_args.do_train:
    #if last_checkpoint is not None:
    #    checkpoint = last_checkpoint
    #elif os.path.isdir(model_args.model_name_or_path):
    #    checkpoint = model_args.model_name_or_path
    #else:
    checkpoint = None
    train_result = trainer.train(resume_from_checkpoint=checkpoint)
    trainer.save_model()

    # save the feature_extractor and the tokenizer
    if is_main_process(training_args.local_rank):
        processor.save_pretrained(training_args.output_dir)

    metrics = train_result.metrics
    max_train_samples = (len(common_voice_train))
    metrics["train_samples"] = min(max_train_samples, len(common_voice_train))

    trainer.log_metrics("train", metrics)
    trainer.save_metrics("train", metrics)
    trainer.save_state()



print("# START TRAINING")
trainer.train()
