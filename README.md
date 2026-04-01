# SharkNet

Software Engineering Project: A university hub where students can ask questions about the campus, similar classes, professors etc.. and a place where students can book tutors and view their reviews.

## How to run this project

### 1. Make sure Python is installed
You need Python 3 installed on your machine. You can check by running:
```
python3 --version
```

### 2. Install Flask
```
pip3 install flask
```

### 3. Start the app
```
python3 app.py
```

### 4. Open it in your browser
Go to:
```
http://127.0.0.1:5000
```
Log in with your NSU email (must end in @mynsu.nova.edu).

## Notes
- The database (`sharknet.db`) is already included in the repo — no setup needed
- If for some reason `sharknet.db` is missing, run `python3 database_setup.py` once to recreate it
- To stop the server press Ctrl+C in the terminal
