# backend/models.py
# -*- coding: utf-8 -*-
"""
===============================================================================
混合深度学习模型库 - 多模型集成和扩展架构
===============================================================================

【文件说明】
本文件提供了多种深度学习模型的混合架构和集成学习方法,
用于扩展基础Transformer模型的预测能力。

【包含的模型】
1. LSTMPredictor: 纯LSTM时间序列预测模型
2. GRUPredictor: 纯GRU时间序列预测模型
3. CNNTransformer: CNN特征提取 + Transformer编码混合模型
4. TransformerLSTM: Transformer编码 + LSTM解码混合模型
5. TransformerGRU: Transformer编码 + GRU解码混合模型

【集成学习方法】
- EnsembleModel: 多模型加权平均集成
- BaggingEnsemble: Bootstrap聚合集成
- StackingEnsemble: 堆叠集成(元学习器)

【使用场景】
1. 对比不同模型在相同数据上的表现
2. 通过模型集成提高预测稳定性和准确性
3. 针对特定股票选择最优模型架构

【工厂方法】
- create_hybrid_model(): 创建混合模型
- create_ensemble_model(): 创建集成模型

【作者】模型库扩展
【更新日期】2024-10
===============================================================================
"""
import torch
import torch.nn as nn
import numpy as np
from typing import List, Tuple, Optional

class LSTMPredictor(nn.Module):
    """LSTM预测模型"""
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, input_size)

    def forward(self, x):
        lstm_out, (h_n, _) = self.lstm(x)
        output = self.fc(lstm_out)
        embedding = h_n[-1]
        return output, embedding

class GRUPredictor(nn.Module):
    """GRU预测模型"""
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 2):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, input_size)

    def forward(self, x):
        gru_out, h_n = self.gru(x)
        output = self.fc(gru_out)
        embedding = h_n[-1]
        return output, embedding

class CNNTransformer(nn.Module):
    """CNN + Transformer混合模型"""
    def __init__(self, input_size: int, d_model: int = 64, nhead: int = 4):
        super().__init__()
        # CNN特征提取器
        self.conv1 = nn.Conv1d(input_size, d_model, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(d_model, d_model, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(d_model)
        self.bn2 = nn.BatchNorm1d(d_model)

        # Transformer编码器
        encoder_layer = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=256, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)

        # 输出层
        self.fc = nn.Linear(d_model, input_size)
        self.relu = nn.ReLU()

    def forward(self, x):
        x_cnn = x.transpose(1, 2)
        x_cnn = self.relu(self.bn1(self.conv1(x_cnn)))
        x_cnn = self.relu(self.bn2(self.conv2(x_cnn)))
        x_cnn = x_cnn.transpose(1, 2)
        x_trans = self.transformer(x_cnn)
        embedding = x_trans.mean(dim=1)
        output = self.fc(x_trans)
        return output, embedding

class TransformerLSTM(nn.Module):
    """Transformer + LSTM混合模型"""
    def __init__(self, input_size: int, d_model: int = 64, nhead: int = 4, hidden_size: int = 128):
        super().__init__()
        # Transformer编码器
        self.input_proj = nn.Linear(input_size, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=256, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)

        # LSTM解码器
        self.lstm = nn.LSTM(d_model, hidden_size, num_layers=2, batch_first=True)
        self.fc = nn.Linear(hidden_size, input_size)

    def forward(self, x):
        x = self.input_proj(x)
        x_trans = self.transformer(x)
        lstm_out, (h_n, _) = self.lstm(x_trans)
        output = self.fc(lstm_out)
        embedding = h_n[-1]
        return output, embedding

class TransformerGRU(nn.Module):
    """Transformer + GRU混合模型"""
    def __init__(self, input_size: int, d_model: int = 64, nhead: int = 4, hidden_size: int = 128):
        super().__init__()
        # Transformer编码器
        self.input_proj = nn.Linear(input_size, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=256, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)

        # GRU解码器
        self.gru = nn.GRU(d_model, hidden_size, num_layers=2, batch_first=True)
        self.fc = nn.Linear(hidden_size, input_size)

    def forward(self, x):
        x = self.input_proj(x)
        x_trans = self.transformer(x)
        gru_out, h_n = self.gru(x_trans)
        output = self.fc(gru_out)
        embedding = h_n[-1]
        return output, embedding

class EnsembleModel:
    """集成学习模型管理器"""

    def __init__(self, models: List[nn.Module], weights: Optional[List[float]] = None):
        """
        Args:
            models: 模型列表
            weights: 每个模型的权重，None则平均权重
        """
        self.models = models
        if weights is None:
            self.weights = [1.0 / len(models)] * len(models)
        else:
            self.weights = weights

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """集成预测"""
        predictions = []
        for model in self.models:
            model.eval()
            with torch.no_grad():
                pred = model(x)
                if isinstance(pred, tuple):
                    pred = pred[0]
                predictions.append(pred)

        # 加权平均
        weighted_pred = torch.zeros_like(predictions[0])
        for pred, weight in zip(predictions, self.weights):
            weighted_pred += pred * weight

        return weighted_pred

    def voting_predict(self, x: torch.Tensor, method: str = 'soft') -> torch.Tensor:
        """投票预测
        Args:
            method: 'soft' 软投票（加权平均），'hard' 硬投票（多数决定）
        """
        predictions = []
        for model in self.models:
            model.eval()
            with torch.no_grad():
                pred = model(x)
                if isinstance(pred, tuple):
                    pred = pred[0]
                predictions.append(pred)

        predictions = torch.stack(predictions)

        if method == 'soft':
            # 软投票：加权平均
            return torch.mean(predictions, dim=0)
        else:
            # 硬投票：取中位数
            return torch.median(predictions, dim=0)[0]

class BaggingEnsemble:
    """Bagging集成学习"""

    def __init__(self, base_model_class, n_estimators: int = 5, **model_kwargs):
        """
        Args:
            base_model_class: 基础模型类
            n_estimators: 基础模型数量
            model_kwargs: 模型初始化参数
        """
        self.models = [base_model_class(**model_kwargs) for _ in range(n_estimators)]
        self.n_estimators = n_estimators

    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 50):
        """训练所有模型（使用bootstrap采样）"""
        n_samples = len(X)

        for model in self.models:
            # Bootstrap采样
            indices = np.random.choice(n_samples, n_samples, replace=True)
            X_boot = X[indices]
            y_boot = y[indices]

            # 训练模型（这里需要根据实际情况实现训练逻辑）
            # train_model(model, X_boot, y_boot, epochs)
            pass

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """集成预测"""
        predictions = []
        for model in self.models:
            model.eval()
            with torch.no_grad():
                pred = model(X)
                if isinstance(pred, tuple):
                    pred = pred[0]
                predictions.append(pred)

        # 平均所有预测
        return torch.mean(torch.stack(predictions), dim=0)

class StackingEnsemble:
    """Stacking集成学习"""

    def __init__(self, base_models: List[nn.Module], meta_model: nn.Module):
        """
        Args:
            base_models: 基础模型列表
            meta_model: 元学习器
        """
        self.base_models = base_models
        self.meta_model = meta_model

    def get_base_predictions(self, x: torch.Tensor) -> torch.Tensor:
        """获取基础模型的预测结果"""
        predictions = []
        for model in self.base_models:
            model.eval()
            with torch.no_grad():
                pred = model(x)
                if isinstance(pred, tuple):
                    pred = pred[0]
                predictions.append(pred)

        # 将所有预测结果拼接作为元学习器的输入
        return torch.cat(predictions, dim=-1)

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """最终预测"""
        # 获取基础模型预测
        base_preds = self.get_base_predictions(x)

        # 元学习器预测
        self.meta_model.eval()
        with torch.no_grad():
            final_pred = self.meta_model(base_preds)

        return final_pred

def create_hybrid_model(model_type: str, input_size: int, **kwargs):
    """创建混合模型

    Args:
        model_type: 'transformer_lstm', 'transformer_gru', 'cnn_transformer'
        input_size: 输入特征维度
    """
    if model_type == 'transformer_lstm':
        return TransformerLSTM(input_size, **kwargs)
    elif model_type == 'transformer_gru':
        return TransformerGRU(input_size, **kwargs)
    elif model_type == 'cnn_transformer':
        return CNNTransformer(input_size, **kwargs)
    else:
        raise ValueError(f"Unknown hybrid model type: {model_type}")

def create_ensemble_model(ensemble_type: str, input_size: int, **kwargs):
    """创建集成模型

    Args:
        ensemble_type: 'voting', 'bagging', 'boosting', 'stacking'
        input_size: 输入特征维度
    """
    if ensemble_type == 'voting':
        # 创建多个不同的模型进行投票
        from main import TransformerAutoencoder
        models = [
            TransformerAutoencoder(input_size, d_model=64, nhead=4, num_layers=2),
            TransformerAutoencoder(input_size, d_model=128, nhead=8, num_layers=3),
            LSTMPredictor(input_size, hidden_size=128),
            GRUPredictor(input_size, hidden_size=128),
        ]
        return EnsembleModel(models)

    elif ensemble_type == 'bagging':
        from main import TransformerAutoencoder
        return BaggingEnsemble(TransformerAutoencoder, n_estimators=5,
                              input_dim=input_size, d_model=64, nhead=4, num_layers=2)

    elif ensemble_type == 'stacking':
        # 创建基础模型
        from main import TransformerAutoencoder
        base_models = [
            TransformerAutoencoder(input_size, d_model=64, nhead=4, num_layers=2),
            LSTMPredictor(input_size),
            GRUPredictor(input_size),
        ]

        # 创建元学习器（输入是3个模型的输出拼接）
        meta_input_size = input_size * len(base_models)
        meta_model = nn.Sequential(
            nn.Linear(meta_input_size, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, input_size)
        )

        return StackingEnsemble(base_models, meta_model)
    else:
        raise ValueError(f"Unknown ensemble type: {ensemble_type}")