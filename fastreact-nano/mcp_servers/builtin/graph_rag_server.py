"""
FastReAct Nano - GraphRAG MCP Server (Enhanced)

MCP server providing knowledge graph tools with rich mock data.
This is a reference implementation for integrating knowledge graph services.
"""

import asyncio
import json
import random
import re
from typing import Any, Dict
from fastreact.mcp.server import SimpleMCPServer


class GraphRAGMCPServer(SimpleMCPServer):
    """
    GraphRAG MCP Server with rich knowledge graph data.

    Provides tools for:
    - Searching the knowledge graph
    - Getting entity details
    - Querying relationships
    - Vector similarity search
    - Creating entities
    """

    def __init__(self):
        """Initialize GraphRAG MCP server"""
        super().__init__()
        self._load_mock_data()
        self._register_tools()

    def _load_mock_data(self):
        """Load rich knowledge graph with entities and relationships"""

        # Add keywords/aliases for better search
        self._entities = {
            # === AI Concepts ===
            "entity_1": {
                "id": "entity_1",
                "name": "Artificial Intelligence",
                "type": "concept",
                "aliases": ["AI", "artificial intelligence", "人工智能", "机器智能"],
                "description": "Simulation of human intelligence processes by machines, especially computer systems. AI enables computers to perform tasks that typically require human intelligence.",
                "keywords": ["intelligence", "smart", "automation", "cognitive", "reasoning"],
                "properties": {
                    "year_discovered": "1956",
                    "field": "Computer Science",
                    "applications": ["NLP", "Computer Vision", "Robotics", "Game Playing", "Expert Systems"],
                    "pioneers": ["Alan Turing", "John McCarthy", "Marvin Minsky"]
                },
                "vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
            },
            "entity_2": {
                "id": "entity_2",
                "name": "Machine Learning",
                "type": "concept",
                "aliases": ["ML", "machine learning", "机器学习", "ML"],
                "description": "Subset of AI that enables systems to learn and improve from experience without being explicitly programmed. ML algorithms build models based on training data.",
                "keywords": ["learning", "training", "data", "algorithms", "models", "prediction", "classification"],
                "properties": {
                    "year_discovered": "1980",
                    "field": "Computer Science",
                    "algorithms": ["Neural Networks", "Decision Trees", "SVM", "Random Forest", "Gradient Boosting"],
                    "types": ["Supervised", "Unsupervised", "Reinforcement", "Deep Learning"]
                },
                "vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
            },
            "entity_3": {
                "id": "entity_3",
                "name": "Deep Learning",
                "type": "concept",
                "aliases": ["DL", "deep learning", "深度学习", "神经网络", "neural networks"],
                "description": "Subset of ML using multi-layered neural networks to learn from vast amounts of data. DL has revolutionized computer vision, NLP, and speech recognition.",
                "keywords": ["neural", "networks", "deep", "layers", "backpropagation", "gradient", "optimization"],
                "properties": {
                    "year_discovered": "2010",
                    "field": "Computer Science",
                    "frameworks": ["TensorFlow", "PyTorch", "Keras", "JAX", "MXNet"],
                    "architectures": ["CNN", "RNN", "Transformer", "GAN", "Autoencoder"]
                },
                "vector": [0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82]
            },
            "entity_4": {
                "id": "entity_4",
                "name": "Natural Language Processing",
                "type": "concept",
                "aliases": ["NLP", "natural language processing", "自然语言处理", "文本处理"],
                "description": "Branch of AI focused on interaction between computers and human language. NLP enables machines to understand, interpret, and generate human language.",
                "keywords": ["language", "text", "speech", "linguistics", "translation", "sentiment", "generation", "understanding"],
                "properties": {
                    "year_discovered": "1950",
                    "field": "Computational Linguistics",
                    "tasks": ["Translation", "Sentiment Analysis", "Text Generation", "Speech Recognition", "Question Answering"],
                    "techniques": ["Tokenization", "Embeddings", "Transformers", "LLMs"]
                },
                "vector": [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.88]
            },
            "entity_5": {
                "id": "entity_5",
                "name": "Computer Vision",
                "type": "concept",
                "aliases": ["CV", "computer vision", "计算机视觉", "图像识别"],
                "description": "Field of AI that trains computers to interpret and understand the visual world. CV enables machines to process and analyze images and videos.",
                "keywords": ["vision", "image", "video", "visual", "recognition", "detection", "segmentation", "tracking"],
                "properties": {
                    "year_discovered": "1960",
                    "field": "Computer Science",
                    "tasks": ["Object Detection", "Image Classification", "Face Recognition", "Image Segmentation", "Style Transfer"],
                    "applications": ["Autonomous Driving", "Medical Imaging", "Surveillance", "AR/VR"]
                },
                "vector": [0.14, 0.24, 0.34, 0.44, 0.54, 0.64, 0.74, 0.84]
            },

            # === Algorithms & Architectures ===
            "entity_6": {
                "id": "entity_6",
                "name": "Neural Networks",
                "type": "algorithm",
                "aliases": ["NN", "neural networks", "神经网络", "人工神经网络", "ANN"],
                "description": "Computing systems inspired by biological neural networks in human brains. NNs are the foundation of deep learning and modern AI.",
                "keywords": ["neuron", "perceptron", "layers", "weights", "activation", "backprop"],
                "properties": {
                    "year_discovered": "1943",
                    "field": "Computational Neuroscience",
                    "types": ["CNN", "RNN", "Transformer", "GAN", "Autoencoder", "Feedforward"],
                    "activation": ["ReLU", "Sigmoid", "Tanh", "Softmax"]
                },
                "vector": [0.16, 0.26, 0.36, 0.46, 0.56, 0.66, 0.76, 0.86]
            },
            "entity_7": {
                "id": "entity_7",
                "name": "Transformers",
                "type": "architecture",
                "aliases": ["Transformer", "transformers", "Transformer架构", "注意力机制"],
                "description": "Deep learning architecture using self-attention mechanisms to process sequential data. Transformers revolutionized NLP and are now used in computer vision and other domains.",
                "keywords": ["attention", "self-attention", "encoder", "decoder", "parallel", "sequence", "BERT", "GPT"],
                "properties": {
                    "year_discovered": "2017",
                    "field": "Deep Learning",
                    "paper": "Attention Is All You Need",
                    "models": ["BERT", "GPT", "T5", "ViT", "Stable Diffusion"],
                    "applications": ["NLP", "Computer Vision", "Speech", "Multimodal"]
                },
                "vector": [0.13, 0.23, 0.33, 0.43, 0.53, 0.63, 0.73, 0.83]
            },
            "entity_8": {
                "id": "entity_8",
                "name": "Convolutional Neural Networks",
                "type": "architecture",
                "aliases": ["CNN", "convolutional neural networks", "卷积神经网络", "ConvNets"],
                "description": "Specialized neural architecture for processing grid-like data such as images. CNNs are widely used in computer vision for image classification, object detection, and segmentation.",
                "keywords": ["convolution", "filters", "kernels", "pooling", "feature maps", "images", "vision"],
                "properties": {
                    "year_discovered": "1989",
                    "field": "Computer Vision",
                    "architectures": ["LeNet", "AlexNet", "VGG", "ResNet", "Inception", "EfficientNet"],
                    "applications": ["Image Classification", "Object Detection", "Style Transfer", "Medical Imaging"]
                },
                "vector": [0.11, 0.21, 0.31, 0.41, 0.51, 0.61, 0.71, 0.81]
            },
            "entity_9": {
                "id": "entity_9",
                "name": "Recurrent Neural Networks",
                "type": "architecture",
                "aliases": ["RNN", "recurrent neural networks", "循环神经网络"],
                "description": "Neural networks designed for sequential data processing. RNNs maintain internal state to process sequences of variable length.",
                "keywords": ["sequential", "recurrent", "LSTM", "GRU", "time series", "sequence"],
                "properties": {
                    "year_discovered": "1986",
                    "field": "Deep Learning",
                    "variants": ["Vanilla RNN", "LSTM", "GRU", "Bidirectional RNN"],
                    "applications": ["Speech Recognition", "Machine Translation", "Time Series Forecasting", "Text Generation"]
                },
                "vector": [0.17, 0.27, 0.37, 0.47, 0.57, 0.67, 0.77, 0.87]
            },

            # === Models & Applications ===
            "entity_10": {
                "id": "entity_10",
                "name": "Large Language Models",
                "type": "model",
                "aliases": ["LLM", "large language models", "大语言模型", "语言模型"],
                "description": "AI models trained on vast amounts of text data to understand and generate human-like text. LLMs have revolutionized natural language processing and generation.",
                "keywords": ["language", "text", "generation", "understanding", "GPT", "BERT", "LLaMA", "Claude", "training", "inference"],
                "properties": {
                    "year_discovered": "2018",
                    "field": "NLP",
                    "examples": ["GPT-4", "Claude", "Llama", "Gemini", "Mistral"],
                    "applications": ["Chat", "Code Generation", "Translation", "Summarization", "Question Answering"]
                },
                "vector": [0.11, 0.21, 0.31, 0.41, 0.51, 0.61, 0.71, 0.81]
            },
            "entity_11": {
                "id": "entity_11",
                "name": "GPT",
                "type": "model",
                "aliases": ["GPT", "Generative Pre-trained Transformer", "GPT模型"],
                "description": "Series of large language models developed by OpenAI. GPT models have set benchmarks in natural language understanding and generation.",
                "keywords": ["GPT", "GPT-3", "GPT-4", "OpenAI", "generation", "chat", "code"],
                "properties": {
                    "year_discovered": "2018",
                    "field": "NLP",
                    "versions": ["GPT-1", "GPT-2", "GPT-3", "GPT-3.5", "GPT-4", "GPT-4o"],
                    "capabilities": ["Text Generation", "Code Generation", "Translation", "Summarization"]
                },
                "vector": [0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82]
            },
            "entity_12": {
                "id": "entity_12",
                "name": "BERT",
                "type": "model",
                "aliases": ["BERT", "Bidirectional Encoder Representations from Transformers"],
                "description": "Transformer-based model designed for pre-training deep bidirectional representations from unlabeled text. BERT excels at understanding tasks.",
                "keywords": ["BERT", "encoder", "bidirectional", "understanding", "classification", "NER", "QA"],
                "properties": {
                    "year_discovered": "2018",
                    "field": "NLP",
                    "variants": ["BERT-Base", "BERT-Large", "RoBERTa", "ALBERT"],
                    "tasks": ["Question Answering", "Named Entity Recognition", "Sentiment Analysis", "Text Classification"]
                },
                "vector": [0.14, 0.24, 0.34, 0.44, 0.54, 0.64, 0.74, 0.84]
            },

            # === Frameworks & Libraries ===
            "entity_13": {
                "id": "entity_13",
                "name": "TensorFlow",
                "type": "framework",
                "aliases": ["TensorFlow", "TF"],
                "description": "Open-source machine learning framework developed by Google. TensorFlow is widely used for building and deploying ML models in production.",
                "keywords": ["TensorFlow", "Google", "framework", "library", "training", "deployment", "TPU"],
                "properties": {
                    "year_discovered": "2015",
                    "field": "Deep Learning",
                    "language": "Python",
                    "applications": ["Computer Vision", "NLP", "Reinforcement Learning"]
                },
                "vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
            },
            "entity_14": {
                "id": "entity_14",
                "name": "PyTorch",
                "type": "framework",
                "aliases": ["PyTorch", "torch"],
                "description": "Open-source machine learning framework developed by Meta (Facebook). PyTorch is known for its dynamic computational graph and ease of use in research.",
                "keywords": ["PyTorch", "Meta", "Facebook", "framework", "research", "dynamic", "GPU"],
                "properties": {
                    "year_discovered": "2016",
                    "field": "Deep Learning",
                    "language": "Python",
                    "features": ["Dynamic Graph", "Pythonic", "Research-friendly", "GPU Acceleration"]
                },
                "vector": [0.16, 0.26, 0.36, 0.46, 0.56, 0.66, 0.76, 0.86]
            },
            "entity_15": {
                "id": "entity_15",
                "name": "Keras",
                "type": "library",
                "aliases": ["Keras"],
                "description": "High-level deep learning API running on top of TensorFlow. Keras provides a user-friendly interface for building and training neural networks.",
                "keywords": ["Keras", "API", "high-level", "simple", "user-friendly", "neural networks"],
                "properties": {
                    "year_discovered": "2015",
                    "field": "Deep Learning",
                    "backend": ["TensorFlow", "JAX", "PyTorch"],
                    "features": ["Sequential API", "Functional API", "Model Zoo"]
                },
                "vector": [0.13, 0.23, 0.33, 0.43, 0.53, 0.63, 0.73, 0.83]
            },

            # === Techniques & Methods ===
            "entity_16": {
                "id": "entity_16",
                "name": "Backpropagation",
                "type": "algorithm",
                "aliases": ["Backprop", "反向传播", "反向传播算法"],
                "description": "Algorithm for training neural networks by calculating gradients. Backpropagation is the foundation of modern deep learning.",
                "keywords": ["backprop", "gradient", "training", "optimization", "neural networks", "chains"],
                "properties": {
                    "year_discovered": "1986",
                    "field": "Deep Learning",
                    "related": ["Gradient Descent", "Chain Rule", "Optimization"]
                },
                "vector": [0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.88]
            },
            "entity_17": {
                "id": "entity_17",
                "name": "Gradient Descent",
                "type": "algorithm",
                "aliases": ["Gradient Descent", "梯度下降", "梯度优化"],
                "description": "Optimization algorithm for minimizing loss functions in machine learning. Gradient descent is the foundation of training neural networks.",
                "keywords": ["gradient", "descent", "optimization", "minimize", "loss", "learning rate"],
                "properties": {
                    "year_discovered": "1847",
                    "field": "Optimization",
                    "variants": ["Batch GD", "Stochastic GD", "Adam", "RMSprop", "AdaGrad"],
                    "applications": ["Neural Networks", "Machine Learning", "Deep Learning"]
                },
                "vector": [0.19, 0.29, 0.39, 0.49, 0.59, 0.69, 0.79, 0.89]
            },
            "entity_18": {
                "id": "entity_18",
                "name": "Regularization",
                "type": "technique",
                "aliases": ["Regularization", "正则化"],
                "description": "Technique to prevent overfitting in machine learning models by adding penalty terms to the loss function. Regularization improves model generalization.",
                "keywords": ["regularization", "overfitting", "generalization", "L1", "L2", "dropout", "early stopping"],
                "properties": {
                    "year_discovered": "1990",
                    "field": "Machine Learning",
                    "methods": ["L1 Regularization", "L2 Regularization", "Dropout", "Early Stopping", "Data Augmentation"],
                    "purpose": "Prevent overfitting, improve generalization"
                },
                "vector": [0.17, 0.27, 0.37, 0.47, 0.57, 0.67, 0.77, 0.87]
            },

            # === Applications ===
            "entity_19": {
                "id": "entity_19",
                "name": "Recommendation Systems",
                "type": "application",
                "aliases": ["Recommendation Systems", "推荐系统", "推荐算法"],
                "description": "Systems that suggest relevant items to users based on their preferences and behavior. Used in e-commerce, streaming, and social media.",
                "keywords": ["recommendation", "suggestion", "personalization", "collaborative filtering", "content-based"],
                "properties": {
                    "year_discovered": "1990",
                    "field": "Machine Learning",
                    "techniques": ["Collaborative Filtering", "Content-Based Filtering", "Hybrid Methods", "Matrix Factorization"],
                    "applications": ["E-commerce", "Netflix", "Amazon", "Spotify"]
                },
                "vector": [0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82]
            },
            "entity_20": {
                "id": "entity_20",
                "name": "Autonomous Driving",
                "type": "application",
                "aliases": ["Autonomous Driving", "自动驾驶", "self-driving"],
                "description": "Ability of vehicles to sense their environment and operate without human intervention. Combines computer vision, sensor fusion, and decision-making.",
                "keywords": ["autonomous", "self-driving", "vehicle", "car", "sensors", "perception", "planning"],
                "properties": {
                    "year_discovered": "2010",
                    "field": "Robotics",
                    "technologies": ["Computer Vision", "Sensor Fusion", "Path Planning", "Control Systems"],
                    "companies": ["Tesla", "Waymo", "Cruise", "NVIDIA"]
                },
                "vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
            },

            # === Projects ===
            "entity_21": {
                "id": "entity_21",
                "name": "AlphaGo",
                "type": "project",
                "aliases": ["AlphaGo"],
                "description": "Computer program developed by DeepMind to play the board game Go. AlphaGo made history by defeating world champion Lee Sedol in 2016.",
                "keywords": ["AlphaGo", "Go", "game", "board game", "DeepMind", "Google", "reinforcement learning"],
                "properties": {
                    "year_discovered": "2016",
                    "field": "Reinforcement Learning",
                    "achievements": ["Defeated Lee Sedol", "Defeated Ke Jie", "Mastered Go"],
                    "techniques": ["Monte Carlo Tree Search", "Reinforcement Learning", "Self-Play"]
                },
                "vector": [0.16, 0.26, 0.36, 0.46, 0.56, 0.66, 0.76, 0.86]
            },
            "entity_22": {
                "id": "entity_22",
                "name": "ImageNet",
                "type": "dataset",
                "aliases": ["ImageNet"],
                "description": "Large visual database designed for use in visual object recognition research. ImageNet contains over 14 million annotated images across 20,000 categories.",
                "keywords": ["ImageNet", "dataset", "images", "classification", "visual recognition", "benchmark"],
                "properties": {
                    "year_discovered": "2010",
                    "field": "Computer Vision",
                    "size": "14M images",
                    "categories": "20,000",
                    "impact": "Revolutionized computer vision, enabled deep learning boom"
                },
                "vector": [0.13, 0.23, 0.33, 0.43, 0.53, 0.63, 0.73, 0.83]
            },
            "entity_23": {
                "id": "entity_23",
                "name": "Attention Mechanism",
                "type": "mechanism",
                "aliases": ["Attention", "注意力机制"],
                "description": "Mechanism that allows neural networks to focus on specific parts of input. Attention is the foundation of Transformers and has revolutionized sequence modeling.",
                "keywords": ["attention", "focus", "weights", "transformer", "self-attention", "mechanism"],
                "properties": {
                    "year_discovered": "2014",
                    "field": "Deep Learning",
                    "types": ["Self-Attention", "Cross-Attention", "Multi-Head Attention"],
                    "applications": ["Transformers", "NLP", "Computer Vision"]
                },
                "vector": [0.14, 0.24, 0.34, 0.44, 0.54, 0.64, 0.74, 0.84]
            },
            "entity_24": {
                "id": "entity_24",
                "name": "Reinforcement Learning",
                "type": "paradigm",
                "aliases": ["RL", "reinforcement learning", "强化学习"],
                "description": "Area of machine learning concerned with how software agents ought to take actions in an environment to maximize cumulative reward.",
                "keywords": ["reinforcement", "reward", "agent", "environment", "policy", "Q-learning", "actor-critic"],
                "properties": {
                    "year_discovered": "1957",
                    "field": "Machine Learning",
                    "algorithms": ["Q-Learning", "Policy Gradients", "Actor-Critic", "PPO", "DQN"],
                    "applications": ["Games", "Robotics", "Autonomous Systems", "Recommendation Systems"]
                },
                "vector": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
            },
            "entity_25": {
                "id": "entity_25",
                "name": "Transfer Learning",
                "type": "technique",
                "aliases": ["Transfer Learning", "迁移学习"],
                "description": "Research problem in machine learning that focuses on storing knowledge gained while solving one problem and applying it to another but related problem.",
                "keywords": ["transfer", "pre-training", "fine-tuning", "domain adaptation", "knowledge transfer"],
                "properties": {
                    "year_discovered": "1993",
                    "field": "Machine Learning",
                    "examples": ["ImageNet pre-training", "BERT fine-tuning", "GPT models"],
                    "benefits": ["Faster training", "Better performance", "Less data required"]
                },
                "vector": [0.16, 0.26, 0.36, 0.46, 0.56, 0.66, 0.76, 0.86]
            }
        }

        # Mock relationships between entities
        self._relationships = [
            # AI -> ML -> DL hierarchy
            {"source": "entity_1", "target": "entity_2", "type": "includes", "weight": 0.95, "description": "AI includes Machine Learning as a subset"},
            {"source": "entity_1", "target": "entity_4", "type": "includes", "weight": 0.90, "description": "AI includes NLP as a subfield"},
            {"source": "entity_1", "target": "entity_5", "type": "includes", "weight": 0.90, "description": "AI includes Computer Vision as a subfield"},
            {"source": "entity_2", "target": "entity_3", "type": "includes", "weight": 0.98, "description": "ML includes Deep Learning as a subset"},
            {"source": "entity_2", "target": "entity_6", "type": "uses", "weight": 0.92, "description": "ML uses Neural Networks algorithms"},
            {"source": "entity_3", "target": "entity_6", "type": "based_on", "weight": 0.99, "description": "Deep Learning is based on Neural Networks"},
            {"source": "entity_3", "target": "entity_7", "type": "uses", "weight": 0.97, "description": "Deep Learning uses Transformers architecture"},
            {"source": "entity_3", "target": "entity_8", "type": "enables", "weight": 0.93, "description": "Deep Learning enables Large Language Models"},

            # NLP & Models
            {"source": "entity_4", "target": "entity_3", "type": "uses", "weight": 0.88, "description": "NLP uses Deep Learning techniques"},
            {"source": "entity_4", "target": "entity_10", "type": "powered_by", "weight": 0.97, "description": "Modern NLP is powered by LLMs"},
            {"source": "entity_10", "target": "entity_7", "type": "architecture", "weight": 0.99, "description": "LLMs use Transformers architecture"},
            {"source": "entity_11", "target": "entity_10", "type": "example_of", "weight": 0.95, "description": "GPT is a Large Language Model"},
            {"source": "entity_12", "target": "entity_10", "type": "example_of", "weight": 0.95, "description": "BERT is a Large Language Model"},

            # CV & Architectures
            {"source": "entity_5", "target": "entity_3", "type": "uses", "weight": 0.94, "description": "Computer Vision uses Deep Learning"},
            {"source": "entity_5", "target": "entity_8", "type": "uses", "weight": 0.85, "description": "Computer Vision uses CNN architecture"},
            {"source": "entity_8", "target": "entity_6", "type": "specialization_of", "weight": 0.91, "description": "CNN is a type of Neural Network"},
            {"source": "entity_9", "target": "entity_6", "type": "specialization_of", "weight": 0.92, "description": "RNN is a type of Neural Network"},
            {"source": "entity_7", "target": "entity_10", "type": "enables", "weight": 0.96, "description": "Transformers enable Large Language Models"},

            # Frameworks
            {"source": "entity_13", "target": "entity_3", "type": "supports", "weight": 0.90, "description": "TensorFlow supports Deep Learning"},
            {"source": "entity_14", "target": "entity_3", "type": "supports", "weight": 0.90, "description": "PyTorch supports Deep Learning"},
            {"source": "entity_15", "target": "entity_13", "type": "built_on", "weight": 0.98, "description": "Keras is built on TensorFlow"},
            {"source": "entity_15", "target": "entity_14", "type": "also_supports", "weight": 0.85, "description": "Keras also supports PyTorch"},

            # Training
            {"source": "entity_16", "target": "entity_6", "type": "used_in", "weight": 0.99, "description": "Backpropagation is used in Neural Networks"},
            {"source": "entity_17", "target": "entity_16", "type": "enables", "weight": 0.98, "description": "Gradient Descent enables Backpropagation"},
            {"source": "entity_18", "target": "entity_2", "type": "improves", "weight": 0.88, "description": "Regularization improves Machine Learning models"},

            # Applications
            {"source": "entity_19", "target": "entity_2", "type": "uses", "weight": 0.92, "description": "Recommendation Systems use Machine Learning"},
            {"source": "entity_20", "target": "entity_5", "type": "uses", "weight": 0.95, "description": "Autonomous Driving uses Computer Vision"},
            {"source": "entity_20", "target": "entity_2", "type": "uses", "weight": 0.90, "description": "Autonomous Driving uses Machine Learning"},
            {"source": "entity_20", "target": "entity_3", "type": "uses", "weight": 0.93, "description": "Autonomous Driving uses Deep Learning"},

            # Famous Projects
            {"source": "entity_21", "target": "entity_24", "type": "used", "weight": 0.96, "description": "AlphaGo used Reinforcement Learning"},
            {"source": "entity_22", "target": "entity_5", "type": "accelerated", "weight": 0.94, "description": "ImageNet accelerated Computer Vision"},
            {"source": "entity_22", "target": "entity_3", "weight": 0.93, "description": "ImageNet drove Deep Learning adoption"},
            {"source": "entity_23", "target": "entity_7", "type": "foundation_of", "weight": 0.99, "description": "Attention Mechanism is the foundation of Transformers"},

            # Transfer Learning
            {"source": "entity_25", "target": "entity_22", "type": "applied_to", "weight": 0.89, "description": "Transfer Learning applied to ImageNet models"},
            {"source": "entity_25", "target": "entity_12", "type": "used_in", "weight": 0.90, "description": "Transfer Learning used in BERT"},
            {"source": "entity_25", "target": "entity_3", "type": "technique_for", "weight": 0.87, "description": "Transfer Learning is a technique for Deep Learning"}
        ]

    def _register_tools(self):
        """Register GraphRAG tools"""

        # Tool 1: Search graph
        self.register_tool(
            name="search_graph",
            description="Search knowledge graph for entities matching query text. Supports searching by name, aliases, description, keywords, and properties.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for entities (supports English and Chinese)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )

        # Tool 2: Get entity details
        self.register_tool(
            name="get_entity",
            description="Get detailed information about a specific entity including its relationships",
            input_schema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID to retrieve (e.g., entity_1, entity_2)"
                    }
                },
                "required": ["entity_id"]
            }
        )

        # Tool 3: Query relationships
        self.register_tool(
            name="query_relationships",
            description="Query relationships between entities in the knowledge graph. Explores connections up to specified depth.",
            input_schema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Source entity ID"
                    },
                    "max_depth": {
                        "type": "number",
                        "description": "Maximum relationship depth (1-3 recommended)",
                        "default": 2
                    }
                },
                "required": ["entity_id"]
            }
        )

        # Tool 4: Vector search
        self.register_tool(
            name="vector_search",
            description="Search entities by vector similarity (semantic search). Finds conceptually similar entities even if keywords don't match.",
            input_schema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "Query text to search"
                    },
                    "top_k": {
                        "type": "number",
                        "description": "Number of similar entities to return",
                        "default": 5
                    }
                },
                "required": ["query_text"]
            }
        )

        # Tool 5: Create entity
        self.register_tool(
            name="create_entity",
            description="Create a new entity in the knowledge graph",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Entity name"
                    },
                    "type": {
                        "type": "string",
                        "description": "Entity type (e.g., project, concept, person, algorithm)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Entity description"
                    },
                    "aliases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Alternative names for the entity (optional)"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords for better search matching (optional)"
                    },
                    "properties": {
                        "type": "object",
                        "description": "Additional entity properties (optional)"
                    }
                },
                "required": ["name", "type", "description"]
            }
        )

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> str:
        """Handle tool calls"""

        if name == "search_graph":
            return await self._search_graph(
                arguments["query"],
                arguments.get("limit", 10)
            )

        elif name == "get_entity":
            return await self._get_entity(arguments["entity_id"])

        elif name == "query_relationships":
            return await self._query_relationships(
                arguments["entity_id"],
                arguments.get("max_depth", 2)
            )

        elif name == "vector_search":
            return await self._vector_search(
                arguments["query_text"],
                arguments.get("top_k", 5)
            )

        elif name == "create_entity":
            return await self._create_entity(
                arguments["name"],
                arguments["type"],
                arguments["description"],
                arguments.get("aliases", []),
                arguments.get("keywords", []),
                arguments.get("properties", {})
            )

        else:
            return json.dumps({
                "error": f"Unknown tool: {name}"
            }, ensure_ascii=False)

    async def _search_graph(self, query: str, limit: int) -> str:
        """Search graph for matching entities (improved matching)"""
        results = []
        query_lower = query.lower()

        # Extract Chinese and English words from query
        import re
        query_words = set(re.findall(r'\w+', query_lower, flags=re.UNICODE))

        for entity_id, entity in self._entities.items():
            score = 0
            match_reasons = []

            # 1. Exact name match (highest priority)
            if query_lower == entity["name"].lower():
                score += 100
                match_reasons.append("exact_name")

            # 2. Alias match
            if "aliases" in entity:
                for alias in entity["aliases"]:
                    if query_lower == alias.lower():
                        score += 90
                        match_reasons.append(f"alias:{alias}")
                    elif query_lower in alias.lower():
                        score += 70
                        match_reasons.append("alias_partial")

            # 3. Partial name match
            if query_lower in entity["name"].lower():
                score += 50
                match_reasons.append("name_partial")

            # 4. Description match
            if query_lower in entity.get("description", "").lower():
                score += 30
                match_reasons.append("description")

            # 5. Keywords match
            if "keywords" in entity:
                for keyword in entity["keywords"]:
                    if query_lower == keyword.lower():
                        score += 40
                        match_reasons.append(f"keyword:{keyword}")
                    elif query_lower in keyword.lower():
                        score += 20
                        match_reasons.append("keyword_partial")

            # 6. Type match
            if query_lower in entity.get("type", "").lower():
                score += 35
                match_reasons.append("type")

            # 7. Properties match (values)
            if "properties" in entity:
                for key, value in entity["properties"].items():
                    if isinstance(value, str) and query_lower in value.lower():
                        score += 25
                        match_reasons.append(f"prop:{key}")
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and query_lower in item.lower():
                                score += 25
                                match_reasons.append(f"prop:{key}:{item}")

            # 8. Word overlap in description
            desc_words = set(re.findall(r'\w+', entity.get("description", "").lower(), flags=re.UNICODE))
            word_overlap = query_words & desc_words
            if word_overlap:
                score += len(word_overlap) * 10
                match_reasons.append(f"words:{','.join(list(word_overlap))}")

            if score > 0:
                results.append({
                    **entity,
                    "match_score": score,
                    "match_reasons": match_reasons
                })

        # Sort by score and return top results
        results.sort(key=lambda x: x["match_score"], reverse=True)

        return json.dumps({
            "query": query,
            "results": results[:limit],
            "count": len(results[:limit])
        }, ensure_ascii=False, indent=2)

    async def _get_entity(self, entity_id: str) -> str:
        """Get entity details"""
        if entity_id in self._entities:
            entity = self._entities[entity_id].copy()

            # Add relationships
            entity["relationships"] = [
                {**r,
                 "source_name": self._entities[r["source"]]["name"],
                 "target_name": self._entities[r["target"]]["name"]}
                for r in self._relationships
                if r["source"] == entity_id or r["target"] == entity_id
            ]

            return json.dumps(entity, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "error": f"Entity not found: {entity_id}",
                "available_entities": list(self._entities.keys())
            }, ensure_ascii=False, indent=2)

    async def _query_relationships(self, entity_id: str, max_depth: int) -> str:
        """Query entity relationships"""
        if entity_id not in self._entities:
            return json.dumps({
                "error": f"Entity not found: {entity_id}"
            }, ensure_ascii=False)

        # Find direct relationships
        relationships = []
        visited = {entity_id}
        current_level = [entity_id]

        for depth in range(max_depth):
            next_level = []

            for source_id in current_level:
                for rel in self._relationships:
                    if rel["source"] == source_id and rel["target"] not in visited:
                        relationships.append({
                            **rel,
                            "depth": depth + 1,
                            "source_name": self._entities[rel["source"]]["name"],
                            "target_name": self._entities[rel["target"]]["name"]
                        })
                        visited.add(rel["target"])
                        next_level.append(rel["target"])

            current_level = next_level

            if not current_level:
                break

        return json.dumps({
            "entity": entity_id,
            "entity_name": self._entities[entity_id]["name"],
            "relationships": relationships,
            "total_count": len(relationships)
        }, ensure_ascii=False, indent=2)

    async def _vector_search(self, query_text: str, top_k: int) -> str:
        """Vector similarity search (improved)"""
        # Pseudo-random but consistent score based on query
        results = []

        # Use hash for consistency but vary by query
        query_hash = sum(ord(c) for c in query_text)

        for entity_id, entity in self._entities.items():
            # Base similarity from entity hash and query hash
            entity_hash = sum(ord(c) for c in entity["name"])
            base_score = 0.6 + ((hash(query_text + entity_id) % 300) / 1000.0)

            # Boost score for keyword/alias matches
            query_lower = query_text.lower()
            boost = 0

            # Keyword match boost
            if "keywords" in entity:
                for keyword in entity["keywords"]:
                    if keyword.lower() in query_lower:
                        boost += 0.05

            # Alias match boost
            if "aliases" in entity:
                for alias in entity["aliases"]:
                    if alias.lower() in query_lower:
                        boost += 0.08

            # Description word overlap
            desc_words = set(re.findall(r'\w+', entity.get("description", "").lower()))
            query_words = set(re.findall(r'\w+', query_lower))
            word_overlap = desc_words & query_words
            if word_overlap:
                boost += len(word_overlap) * 0.02

            similarity = min(0.99, base_score + boost)

            results.append({
                **entity,
                "similarity": round(similarity, 4)
            })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Return top_k
        return json.dumps({
            "query": query_text,
            "results": results[:top_k],
            "count": len(results[:top_k])
        }, ensure_ascii=False, indent=2)

    async def _create_entity(self, name: str, type: str, description: str, aliases: list, keywords: list, properties: Dict[str, Any]) -> str:
        """Create a new entity in the knowledge graph"""
        try:
            # Generate new entity ID
            entity_id = f"entity_{len(self._entities) + 1}"

            # Create vector embedding (mock)
            vector = [
                random.random() * 0.1 + 0.1,
                random.random() * 0.1 + 0.2,
                random.random() * 0.1 + 0.3,
                random.random() * 0.1 + 0.4,
                random.random() * 0.1 + 0.5,
                random.random() * 0.1 + 0.6,
                random.random() * 0.1 + 0.7,
                random.random() * 0.1 + 0.8
            ]

            # Create entity
            entity = {
                "id": entity_id,
                "name": name,
                "type": type,
                "description": description,
                "aliases": aliases,
                "keywords": keywords,
                "properties": properties,
                "vector": vector
            }

            # Add to entities
            self._entities[entity_id] = entity

            return json.dumps({
                "success": True,
                "message": f"Entity '{name}' created successfully",
                "entity_id": entity_id,
                "entity": entity
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"Failed to create entity: {str(e)}"
            }, ensure_ascii=False, indent=2)


# Server entry point
async def main():
    """Run GraphRAG MCP server"""
    server = GraphRAGMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
