import numpy as np
import pandas as pd
def predict_with_model(model, scaler, df_new: pd.DataFrame, features: list) -> pd.Series:
    """
    使用训练好的模型对新数据进行预测

    参数:
    - model: 训练好的模型
    - scaler: 训练时使用的 StandardScaler
    - df_new: 新的数据 (DataFrame)，包含特征列
    - features: 特征列名

    返回:
    - pd.Series: 预测结果（股价）
    """
    # 提取特征并标准化
    X_new = df_new[features]
    X_new_scaled = scaler.transform(X_new)

    # 预测
    predictions = model.predict(X_new_scaled)

    return pd.Series(predictions, index=df_new.index, name="predicted_price")
