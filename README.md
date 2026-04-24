# ⚓ Anchor Cloud

**Zero-Knowledge Encrypted File Vault**

Anchor Cloud is a professional-grade cloud storage platform that prioritizes privacy. Unlike traditional cloud providers, Anchor Cloud uses a **zero-knowledge architecture**, ensuring that your files are encrypted client-side before they ever touch the server. 

> *Your files. Encrypted. Infinite. Unreachable.*

---

## 🏗 Key Features

* **Zero-Knowledge Encryption:** Files are encrypted using AES-256-EAX before upload. The server never sees plaintext files or encryption keys.
* **Hidden Chat Engine:** A unique storage abstraction where every file upload is treated as an encrypted message in a private vault, keeping storage invisible to database inspection.
* **Modern Dashboard:** Sleek, glassmorphic UI designed for an intuitive user experience.
* **Secure Auth:** Multi-factor ready, featuring JWT-based session management and Google OAuth 2.0 integration.

---

## 🛠 Tech Stack

**Backend:**
* **Framework:** FastAPI (Python)
* **Encryption:** PyCryptodome (AES-256-EAX)
* **ORM:** SQLAlchemy (MySQL)

**Frontend:**
* **Interface:** Vanilla HTML5 / CSS3 / JavaScript
* **Design:** Glassmorphism UI
* **Icons:** Lucide Icons

---

## 🚀 Quick Start

### 1. Setup Environment
Clone the repository and prepare your virtual environment:

```bash
git clone [https://github.com/AnchorCloud1/Anchor-Cloud.git](https://github.com/AnchorCloud1/Anchor-Cloud.git)
cd Anchor-Cloud

python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
=======
# Anchor-Cloud
Anchor Cloud is a zero-knowledge file vault using AES-256 client-side encryption. It keeps your data private and unreachable to unauthorized users. With a sleek glassmorphic UI, it's the secure, modern way to manage your sensitive files.
