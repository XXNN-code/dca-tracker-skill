# Google Cloud API 设置指南

## 步骤

### 1. 创建 Google Cloud 项目

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 点击顶部的项目选择器 → **新建项目**
3. 项目名称填 `DCA-Tracker`，点击 **创建**

### 2. 启用 API

1. 在左侧菜单中选择 **API 和服务** → **库**
2. 搜索并启用以下两个 API：
   - **Google Sheets API**
   - **Google Drive API**

### 3. 创建服务账户

1. 进入 **API 和服务** → **凭据**
2. 点击 **创建凭据** → **服务账户**
3. 填写服务账户名称（如 `dca-tracker-bot`）
4. 点击 **完成**

### 4. 生成密钥

1. 点击刚创建的服务账户
2. 进入 **密钥** 标签页
3. 点击 **添加密钥** → **创建新密钥** → 选择 **JSON**
4. 下载密钥文件
5. 将文件重命名为 `service_account.json`
6. 放入项目的 `credentials/` 目录

### 5. 初始化 Sheet

运行以下命令，程序会自动创建 Google Sheet：

```python
from dca_tracker.sheets import init_sheet
url = init_sheet(share_email="你的邮箱@gmail.com")
print(f"Sheet URL: {url}")
```

打开返回的 URL 即可在 Google Sheets 中查看数据。

## 注意事项

- `credentials/` 目录已在 `.gitignore` 中，密钥文件不会被提交到 git
- 服务账户创建的 Sheet 默认只有服务账户自己能访问，需要通过 `share_email` 参数共享给你的 Google 账号
