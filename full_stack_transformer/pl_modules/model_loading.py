import copy
import pathlib
from typing import Optional, Union, Dict

import torch
import transformers

from full_stack_transformer.text_generator.text_generator import TextGenerator
from full_stack_transformer.tokenization import get_tokenizer


def load_transformer_model_from_pl_checkpoint(
        ckpt: Dict,
        device: Union[torch.device, str]) -> transformers.PreTrainedModel:
    model_config = _load_model_config_from_ckpt(ckpt)
    tokenizer = load_tokenizer_from_checkpoint(ckpt)

    model = initialize_transformer_model_from_config(
        config=model_config,
        vocab_size=tokenizer.get_vocab_size())

    model_state_dict = _load_state_dict_from_ckpt(ckpt)
    model.load_state_dict(model_state_dict)
    model = model.to(device)
    return model


def load_text_generator_from_pl_checkpoint(
        ckpt: Dict,
        device: Union[torch.device, str]) -> TextGenerator:
    model = load_transformer_model_from_pl_checkpoint(ckpt=ckpt, device=device)
    tokenizer = load_tokenizer_from_checkpoint(ckpt=ckpt)
    generator = TextGenerator(model=model, tokenizer=tokenizer)
    return generator


def load_transformer_model_from_path(
        model_path: Union[str, pathlib.Path],
        vocab_size: Optional[int]) -> transformers.PreTrainedModel:
    config = transformers.AutoConfig.from_pretrained(model_path)
    modified_config = _modify_transformers_config(config)

    model = transformers.AutoModelForPreTraining.from_pretrained(
        pretrained_model_name_or_path=model_path, config=modified_config)

    _resize_embeddings_if_needed(model, vocab_size)

    return model


def initialize_transformer_model_from_config(
        config: transformers.PretrainedConfig,
        vocab_size: Optional[int]) -> transformers.PreTrainedModel:
    modified_config = _modify_transformers_config(config)
    model = transformers.AutoModelForPreTraining.from_config(modified_config)

    _resize_embeddings_if_needed(model, vocab_size)

    return model


def load_tokenizer_from_checkpoint(ckpt):
    description = ckpt['hparams']['description']
    tokenizer_cls_name = description['Dataset']['tokenizer_cls_name']
    tokenizer = get_tokenizer(tokenizer_cls_name)
    return tokenizer


def _load_model_config_from_ckpt(ckpt):
    model_config = ckpt['hparams']['transformer_config']
    return model_config


def _load_state_dict_from_ckpt(ckpt):
    pl_state_dict = ckpt['state_dict']
    model_state_dict = {}
    for k, v in pl_state_dict.items():
        model_state_dict['.'.join(k.split('.')[1:])] = v

    return model_state_dict


def _modify_transformers_config(
        config: transformers.PretrainedConfig) -> transformers.PretrainedConfig:
    config_copy = copy.deepcopy(config)
    config_copy.output_past = True
    config_copy.output_hidden_states = True
    return config_copy


def _resize_embeddings_if_needed(
        model: transformers.PreTrainedModel,
        vocab_size: int) -> None:
    if vocab_size is not None:
        model.resize_token_embeddings(vocab_size)
