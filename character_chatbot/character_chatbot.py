# import pandas as pd
# import torch
# import re
# import huggingface_hub
# from datasets import Dataset
# import transformers
# from transformers import (
#     BitsAndBytesConfig,
#     AutoModelForCausalLM,
#     AutoTokenizer,
# )
# from peft import LoraConfig, PeftModel
# from trl import SFTConfig, SFTTrainer
# import gc

# # Remove actions from transcript
# def remove_paranthesis(text):
#     result = re.sub(r'\(.*?\)','',text)
#     return result

# class CharacterChatBot():

#     def __init__(self,
#                  model_path,
#                  data_path="/content/data/naruto.csv",
#                  huggingface_token = None
#                  ):
        
#         self.model_path = model_path
#         self.data_path = data_path
#         self.huggingface_token = huggingface_token
#         self.base_model_path = "meta-llama/Meta-Llama-3-8B-Instruct"
#         self.device = "cuda" if torch.cuda.is_available() else "cpu"

#         if self.huggingface_token is not None:
#             huggingface_hub.login(self.huggingface_token)
        
#         if huggingface_hub.repo_exists(self.model_path):
#             self.model = self.load_model(self.model_path)
#         else:
#             print("Model Not found in huggingface hub we will train out own model")
#             train_dataset = self.load_data()
#             self.train(self.base_model_path, train_dataset)
#             self.model = self.load_model(self.model_path)
    
#     def chat(self, message, history):
#         messages = []
#         # Add the system ptomp 
#         messages.append({"role":"system","content":""""Your are Naruto from the anime "Naruto". Your responses should reflect his personality and speech patterns \n"""})

#         for message_and_respnse in history:
#             messages.append({"role":"user","content":message_and_respnse[0]})
#             messages.append({"role":"assistant","content":message_and_respnse[1]})
        
#         messages.append({"role":"user","content":message})

#         terminator = [
#             self.model.tokenizer.eos_token_id,
#             self.model.tokenizer.convert_tokens_to_ids("<|eot_id|>")
#         ]

#         output = self.model(
#             messages,
#             max_length=256,
#             eos_token_id=terminator,
#             do_sample=True,
#             temperature=0.6,
#             top_p=0.9
#         )

#         output_message = output[0]['generated_text'][-1]
#         return output_message


#     def load_model(self, model_path):
#         bnb_config = BitsAndBytesConfig(
#             load_in_4bit=True,
#             bnb_4bit_quant_type="nf4",
#             bnb_4bit_compute_dtype=torch.float16,
#         )
#         pipeline = transformers.pipeline("text-generation",
#                                          model = model_path,
#                                          model_kwargs={"torch_dtype":torch.float16,
#                                                        "quantization_config":bnb_config,
#                                                        }
#                                          )
#         return pipeline
    
#     def train(self,
#               base_model_name_or_path,
#               dataset,
#               output_dir = "./results",
#               per_device_train_batch_size = 1,
#               gradient_accumulation_steps = 1,
#               optim = "paged_adamw_32bit",
#               save_steps = 200,
#               logging_steps = 10,
#               learning_rate = 2e-4,
#               max_grad_norm = 0.3,
#               max_steps = 300,
#               warmup_ratio = 0.3,
#               lr_scheduler_type = "constant",
#               ):
        
#         bnb_config = BitsAndBytesConfig(
#             load_in_4bit=True,
#             bnb_4bit_quant_type="nf4",
#             bnb_4bit_compute_dtype=torch.float16,
#         )

#         model = AutoModelForCausalLM.from_pretrained(base_model_name_or_path, 
#                                                      quantization_config= bnb_config,
#                                                      trust_remote_code=True)
#         model.config.use_cache = False

#         toknizer = AutoTokenizer.from_pretrained(base_model_name_or_path)
#         toknizer.pad_token = toknizer.eos_token

#         lora_alpha = 16
#         lora_dropout = 0.1
#         lora_r=64

#         peft_config = LoraConfig(
#             lora_alpha=lora_alpha,
#             lora_dropout=lora_dropout,
#             r=lora_r,
#             bias="none",
#             task_type="CASUAL_LM"
#         )

#         training_arguments = SFTConfig(
#         output_dir=output_dir,
#         per_device_train_batch_size = per_device_train_batch_size,
#         gradient_accumulation_steps = gradient_accumulation_steps,
#         optim = optim,
#         save_steps = save_steps,
#         logging_steps = logging_steps,
#         learning_rate = learning_rate,
#         fp16= True,
#         max_grad_norm = max_grad_norm,
#         max_steps = max_steps,
#         warmup_ratio = warmup_ratio,
#         group_by_length = True,
#         lr_scheduler_type = lr_scheduler_type,
#         report_to = "none"
#         )

#         max_seq_len = 512

#         trainer = SFTTrainer(
#             model = model,
#             train_dataset=dataset,
#             peft_config=peft_config,
#             dataset_text_field="prompt",
#             max_seq_length=max_seq_len,
#             tokenizer=toknizer,
#             args = training_arguments,
#         )

#         trainer.train()

#         # Save model 
#         trainer.model.save_pretrained("final_ckpt")
#         toknizer.save_pretrained("final_ckpt")

#         # Flush memory
#         del trainer, model
#         gc.collect()

#         base_model = AutoModelForCausalLM.from_pretrained(base_model_name_or_path,
#                                                           return_dict=True,
#                                                           quantization_config=bnb_config,
#                                                           torch_dtype = torch.float16,
#                                                           device_map = self.device
#                                                           )
        
#         tokenizer = AutoTokenizer.from_pretrained(base_model_name_or_path)

#         model = PeftModel.from_pretrained(base_model,"final_ckpt")
#         model.push_to_hub(self.model_path)
#         tokenizer.push_to_hub(self.model_path)

#         # Flush Memory
#         del model, base_model
#         gc.collect()

#     def load_data(self):
#         naruto_transcript_df = pd.read_csv(self.data_path)
#         naruto_transcript_df = naruto_transcript_df.dropna()
#         naruto_transcript_df['line'] = naruto_transcript_df['line'].apply(remove_paranthesis)
#         naruto_transcript_df['number_of_words'] = naruto_transcript_df['line'].str.strip().str.split(" ")
#         naruto_transcript_df['number_of_words'] = naruto_transcript_df['number_of_words'].apply(lambda x: len(x))
#         naruto_transcript_df['naruto_response_flag'] = 0
#         naruto_transcript_df.loc[(naruto_transcript_df['name']=="Naruto")&(naruto_transcript_df['number_of_words']>5),'naruto_response_flag']=1

#         indexes_to_take = list(naruto_transcript_df[(naruto_transcript_df['naruto_response_flag']==1)&(naruto_transcript_df.index>0)].index)

#         system_promt = """" Your are Naruto from the anime "Naruto". Your responses should reflect his personality and speech patterns \n"""
#         prompts = []
#         for ind in indexes_to_take:
#             prompt = system_promt

#             prompt += naruto_transcript_df.iloc[ind -1]['line']
#             prompt += '\n'
#             prompt += naruto_transcript_df.iloc[ind]['line']
#             prompts.append(prompt)
        
#         df = pd.DataFrame({"prompt":prompts})
#         dataset = Dataset.from_pandas(df)

#         return dataset

import pandas as pd
import torch
import re
import huggingface_hub
from datasets import Dataset
import transformers
from transformers import (
    BitsAndBytesConfig,
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments
)
from peft import LoraConfig, PeftModel
import gc

# Remove actions from transcript
def remove_paranthesis(text):
    result = re.sub(r'\(.*?\)', '', text)
    return result

class CharacterChatBot():
    def __init__(self,
                 model_path,
                 data_path="/content/data/naruto.csv",
                 huggingface_token=None):
        
        self.model_path = model_path
        self.data_path = data_path
        self.huggingface_token = huggingface_token
        self.base_model_path = "meta-llama/Meta-Llama-3-8B-Instruct"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if self.huggingface_token is not None:
            huggingface_hub.login(self.huggingface_token)
        
        if huggingface_hub.repo_exists(self.model_path):
            self.model = self.load_model(self.model_path)
        else:
            print("Model not found on Hugging Face Hub; training a new model...")
            train_dataset = self.load_data()
            self.train(self.base_model_path, train_dataset)
            self.model = self.load_model(self.model_path)
    
    def chat(self, message, history):
        messages = []
        # Add system prompt
        messages.append({
            "role": "system",
            "content": "You are Naruto from the anime 'Naruto'. Your responses should reflect his personality and speech patterns.\n"
        })
        for user_msg, bot_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": bot_msg})
        messages.append({"role": "user", "content": message})

        terminator = [
            self.model.tokenizer.eos_token_id,
            self.model.tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]

        output = self.model(
            messages,
            max_length=256,
            eos_token_id=terminator,
            do_sample=True,
            temperature=0.6,
            top_p=0.9
        )
        output_message = output[0]['generated_text'][-1]
        return output_message

    def load_model(self, model_path):
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        pipe = transformers.pipeline("text-generation",
                                       model=model_path,
                                       model_kwargs={
                                           "torch_dtype": torch.float16,
                                           "quantization_config": bnb_config
                                       })
        return pipe

    def train(self,
              base_model_name_or_path,
              dataset,
              output_dir="./results",
              per_device_train_batch_size=1,
              gradient_accumulation_steps=1,
              optim="paged_adamw_32bit",
              save_steps=200,
              logging_steps=10,
              learning_rate=2e-4,
              max_grad_norm=0.3,
              max_steps=300,
              warmup_ratio=0.3,
              lr_scheduler_type="constant"):
        
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )

        # Load base model with quantization config
        model = AutoModelForCausalLM.from_pretrained(
            base_model_name_or_path, 
            quantization_config=bnb_config,
            trust_remote_code=True
        )
        model.config.use_cache = False

        tokenizer = AutoTokenizer.from_pretrained(base_model_name_or_path)
        tokenizer.pad_token = tokenizer.eos_token

        # Setup PEFT (LoRA configuration)
        peft_config = LoraConfig(
            lora_alpha=16,
            lora_dropout=0.1,
            r=64,
            bias="none",
            task_type="CAUSAL_LM"
        )
        
        # Attach trainable adapters to the quantized model
        from peft import prepare_model_for_kbit_training, get_peft_model
        model = prepare_model_for_kbit_training(model)
        model = get_peft_model(model, peft_config)

        # Use standard Hugging Face Trainer for fine-tuning
        training_args = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            learning_rate=learning_rate,
            max_steps=max_steps,
            warmup_ratio=warmup_ratio,
            logging_steps=logging_steps,
            save_steps=save_steps,
            fp16=True,
            optim=optim,
            report_to="none",
            remove_unused_columns=False  # Prevent removal of extra columns
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=tokenizer  # Future: use `processing_class` instead
        )

        trainer.train()

        # Save model and tokenizer locally
        trainer.save_model("final_ckpt")
        tokenizer.save_pretrained("final_ckpt")

        # Free memory
        del trainer, model
        gc.collect()

        # Reload base model to push to hub
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name_or_path,
            return_dict=True,
            quantization_config=bnb_config,
            torch_dtype=torch.float16,
            device_map=self.device
        )
        tokenizer = AutoTokenizer.from_pretrained(base_model_name_or_path)

        # Load the fine-tuned model with PEFT adapters
        model = PeftModel.from_pretrained(base_model, "final_ckpt")
        model.push_to_hub(self.model_path)
        tokenizer.push_to_hub(self.model_path)

        del model, base_model
        gc.collect()

    def load_data(self):
        # Load and clean the CSV
        naruto_transcript_df = pd.read_csv(self.data_path)
        naruto_transcript_df = naruto_transcript_df.dropna()
        naruto_transcript_df['line'] = naruto_transcript_df['line'].apply(remove_paranthesis)
        naruto_transcript_df['number_of_words'] = naruto_transcript_df['line'].str.strip().str.split(" ")
        naruto_transcript_df['number_of_words'] = naruto_transcript_df['number_of_words'].apply(lambda x: len(x))
        naruto_transcript_df['naruto_response_flag'] = 0
        naruto_transcript_df.loc[
            (naruto_transcript_df['name'] == "Naruto") & (naruto_transcript_df['number_of_words'] > 5),
            'naruto_response_flag'
        ] = 1

        indexes_to_take = list(naruto_transcript_df[
            (naruto_transcript_df['naruto_response_flag'] == 1) & (naruto_transcript_df.index > 0)
        ].index)

        system_prompt = """You are Naruto from the anime "Naruto". Your responses should reflect his personality and speech patterns.\n"""
        prompts = []
        for ind in indexes_to_take:
            prompt = system_prompt
            prompt += naruto_transcript_df.iloc[ind - 1]['line'] + '\n'
            prompt += naruto_transcript_df.iloc[ind]['line']
            prompts.append(prompt)
        
        # Create a DataFrame with the prompts
        df = pd.DataFrame({"prompt": prompts})
        dataset = Dataset.from_pandas(df)
        
        # Load the tokenizer from the base model path
        tokenizer = AutoTokenizer.from_pretrained(self.base_model_path)
        # Ensure that the tokenizer has a pad token; if not, set it to the EOS token or add one.
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Define a tokenize function that applies truncation, padding, and adds labels
        def tokenize_function(examples):
            tokenized = tokenizer(examples["prompt"], truncation=True, padding=True, max_length=512)
            # For causal language modeling, use input_ids as labels
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized
        
        # Map the tokenize function over the dataset in batches, and remove the original "prompt" column
        tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["prompt"])
        
        return tokenized_dataset



