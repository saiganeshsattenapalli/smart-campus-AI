from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
import numpy as np
import os, random, string
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

app = FastAPI()

# Ensure folders exist
for folder in ["static", "templates"]:
    os.makedirs(folder, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- ML MODEL SETUP ---
# Mapping categories to numbers for the math: 0: Academic, 1: Hostel, 2: Mess, 3: Infra
X_train = np.array([[0], [1], [2], [3]]) 
y_train = np.array([2, 5, 3, 7]) # Days to resolve
model = LinearRegression().fit(X_train, y_train)

def predict_days(cat):
    mapping = {"Academic": 0, "Hostel": 1, "Mess": 2, "Infrastructure": 3}
    prediction = model.predict([[mapping.get(cat, 0)]])
    return round(float(prediction[0]), 1)

# --- ROUTES ---

# 1. Home Selection Page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 2. Student Portal with Captcha Login
@app.get("/student-login", response_class=HTMLResponse)
async def student_login_page(request: Request):
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return templates.TemplateResponse("student_login.html", {"request": request, "captcha": captcha_text})

@app.api_route("/student-portal", methods=["GET", "POST"], response_class=HTMLResponse)
async def student_portal(request: Request, user_captcha: str = Form(None), real_captcha: str = Form(None)):
    if request.method == "POST" and user_captcha != real_captcha:
        return HTMLResponse("<h2>Captcha Failed! <a href='/student-login'>Try again</a></h2>")
    return templates.TemplateResponse("student_portal.html", {"request": request})

# 3. Raise Complaint (AI Prediction)
@app.get("/raise-complaint", response_class=HTMLResponse)
async def complaint_form(request: Request):
    return templates.TemplateResponse("complaint_form.html", {"request": request})

@app.post("/submit-complaint")
async def save_complaint(request: Request, category: str = Form(...), description: str = Form(...)):
    days = predict_days(category)
    # Added 'Status' for the Faculty checkmark feature
    new_data = {"Category": category, "Description": description, "Days": days, "Status": "Pending"}
    df = pd.DataFrame([new_data])
    df.to_csv("complaints.csv", mode='a', header=not os.path.exists("complaints.csv"), index=False)
    return templates.TemplateResponse("success.html", {"request": request, "days": days, "category": category})

# 4. Feedback (Privacy Focused)
@app.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request):
    return templates.TemplateResponse("feedback_form.html", {"request": request})

@app.post("/submit-feedback")
async def save_feedback(request: Request, name: str = Form(None), rating: str = Form(...), comment: str = Form(...)):
    # If name is empty, mark as Anonymous
    student_name = name if name else "Anonymous"
    new_feed = {"Name": student_name, "Rating": rating, "Comment": comment}
    df = pd.DataFrame([new_feed])
    df.to_csv("feedback.csv", mode='a', header=not os.path.exists("feedback.csv"), index=False)
    return HTMLResponse("<div style='text-align:center;padding:50px;'><h2>Feedback Submitted!</h2><a href='/student-portal'>Back to Portal</a></div>")

# 5. Faculty Section (Secure)
@app.get("/faculty-login", response_class=HTMLResponse)
async def faculty_login_view(request: Request):
    return templates.TemplateResponse("faculty_login.html", {"request": request})

@app.post("/faculty-portal", response_class=HTMLResponse)
async def faculty_dashboard(request: Request, password: str = Form(...)):
    if password != "admin123":
        return HTMLResponse("<h2>Incorrect Password! <a href='/faculty-login'>Try Again</a></h2>")
    
    comp_df = pd.read_csv("complaints.csv") if os.path.exists("complaints.csv") else pd.DataFrame()
    feed_df = pd.read_csv("feedback.csv") if os.path.exists("feedback.csv") else pd.DataFrame()
    
    total = len(comp_df) if not comp_df.empty else 0
    
    if not comp_df.empty:
        plt.figure(figsize=(6, 4))
        comp_df['Category'].value_counts().plot(kind='bar', color='#4e73df')
        plt.title("Complaints Volume")
        plt.tight_layout()
        plt.savefig("static/chart.png")
        plt.close()

    return templates.TemplateResponse("faculty.html", {
        "request": request, 
        "total": total,
        "complaints": comp_df.to_dict(orient="records") if not comp_df.empty else [],
        "feedbacks": feed_df.to_dict(orient="records") if not feed_df.empty else []
    })

# 6. Mark Solved Feature
@app.post("/solve-complaint/{index}")
async def solve_complaint(index: int):
    if os.path.exists("complaints.csv"):
        df = pd.read_csv("complaints.csv")
        if index < len(df):
            df.at[index, 'Status'] = 'SOLVED ✅'
            df.to_csv("complaints.csv", index=False)
    
    return HTMLResponse("""
        <div style="text-align:center; padding:50px; font-family:sans-serif;">
            <h2 style="color:green;">Status Updated!</h2>
            <a href="/faculty-login">Return to Faculty Dashboard (Requires Login)</a>
        </div>
    """)
