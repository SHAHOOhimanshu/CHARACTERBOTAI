from transformers import AutoConfig

# Replace "distilbert-base-uncased" with your base model if different
config = AutoConfig.from_pretrained("distilbert-base-uncased", num_labels=3)
config.save_pretrained(".")
