from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd
def train_model(df: pd.DataFrame, features: list, target: str, test_size: float = 0.2, random_state: int = 42):
    """
    训练股价预测模型，并返回模型和标准化器

    返回:
    - rf_model: 训练好的随机森林回归模型
    - scaler: 用于标准化特征的 StandardScaler
    - X_test_scaled: 测试集特征数据（标准化后）
    - y_test: 测试集目标数据
    - y_pred: 模型对测试集的预测结果
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error, r2_score

    X = df[features]
    y = df[target]

    # 划分训练/测试集
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 训练模型
    rf_model = RandomForestRegressor(n_estimators=100, random_state=random_state)
    rf_model.fit(X_train_scaled, y_train)

    # 预测
    y_pred = rf_model.predict(X_test_scaled)

    # 打印指标
    print("MSE:", mean_squared_error(y_test, y_pred))
    print("R²:", r2_score(y_test, y_pred))

    return rf_model, scaler, X_test_scaled, y_test, y_pred


