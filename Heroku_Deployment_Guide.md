# Deploying Your Dash App to Heroku

This guide will help you deploy your Dash web application to [Heroku](https://www.heroku.com/).

---

## 1. Project Files & Dependencies

Ensure your project root contains the following files:

### **requirements.txt**
List all your dependencies. Example:
```txt
dash
dash-bootstrap-components
pandas
plotly
scikit-learn
gunicorn
```
*Add any other packages you use. Pin versions if you want reproducibility.*

---

### **Procfile**
Tells Heroku how to run your app. Create a file named `Procfile` (no extension, capital P) with this line:
```txt
web: gunicorn app:app.server
```
- `app` is your Python file name (without `.py`)
- `app.server` is needed for Dash/Flask apps

[More on Procfile](https://devcenter.heroku.com/articles/procfile)

---

### **runtime.txt** (optional, but recommended)
Specify your Python version. Example:
```txt
python-3.11.8
```
[Supported Python versions](https://devcenter.heroku.com/articles/python-support#supported-runtimes)

---

## 2. Heroku Setup Steps

1. **Install Heroku CLI**  
   [Download & install Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)

2. **Login to Heroku**
   ```sh
   heroku login
   ```

3. **Initialize Git (if not already)**
   ```sh
   git init
   git add .
   git commit -m "Initial commit"
   ```

4. **Create a Heroku app**
   ```sh
   heroku create your-app-name
   ```

5. **Deploy to Heroku**
   ```sh
   git push heroku master
   ```
   *(or `git push heroku main` if your branch is named main)*

6. **Open your app**
   ```sh
   heroku open
   ```

---

## 3. Checklist

- [x] `requirements.txt` (with all dependencies)
- [x] `Procfile`
- [x] `runtime.txt` (optional, but helps with Python version)
- [x] All your code in the root directory (e.g., `app.py`)
- [x] No hardcoded file paths or local-only dependencies

---

## 4. Useful Links

- [Heroku Python Support](https://devcenter.heroku.com/categories/python-support)
- [Deploying Python and Dash Apps on Heroku (Official Guide)](https://dash.plotly.com/deployment)
- [Heroku CLI Reference](https://devcenter.heroku.com/articles/heroku-cli-commands)

---

If you need help generating any of these files, let me know! 