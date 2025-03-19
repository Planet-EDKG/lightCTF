# **Note:** This repository is still under development. Not all features are supported yet.

# 🎯 LightCTF - A Lightweight CTF Framework

A modern, lightweight Capture The Flag (CTF) framework built with Flask, designed for educational purposes and competitive cybersecurity training.

## 🌟 Features

- **User Management**
  - Role-based access control (Admin/Player)
  - Secure authentication system
  - User registration and login

- **Challenge System**
  - Dynamic challenge creation and management
  - Point-based scoring system
  - Progress tracking per user
  - Real-time feedback on submissions

- **Administrative Tools**
  - Challenge import/export via JSON
  - User management interface
  - Scoreboard monitoring
  - Black market system for special items

- **Modern UI**
  - Responsive design
  - Clean and intuitive interface
  - Progress visualization
  - Flash message system for user feedback

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Flask
- SQLite3

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/lightCTF.git
cd lightCTF
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

### Docker Deployment

To run using Docker:
```bash
docker build -t lightctf .
docker run -p 5000:5000 lightctf
```

## 🏗️ Project Structure

```
lightCTF/
├── app.py              # Application entry point
├── config.py           # Configuration settings
├── database.py         # Database operations
├── routes.py           # Route definitions
├── static/             # Static assets (CSS, JS)
├── templates/          # HTML templates
├── uploads/            # Upload directory
└── challenges.json     # Default challenges
```

## 👥 Default Users

- Admin Account:
  - Username: admin
  - Password: adminpass

- Test User Account:
  - Username: user
  - Password: userpass

## 🔧 Configuration

Edit `config.py` to modify:
- Secret key
- Upload folder location
- Allowed file extensions
- Other application settings

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions, problems and feature requests are not yet welcome! See you in the future.

## 📬 Contact

Created by PlanetEDKG - feel free to contact me!

---

⭐ Star this repo if you find it helpful!
