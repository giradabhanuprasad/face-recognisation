# Employee Attendance System with Face Recognition

A modern, web-based employee attendance management system that uses facial recognition technology for automated attendance tracking. Built with Flask, PostgreSQL, and advanced face recognition libraries.

## 🚀 Features

### Core Functionality
- **Face Recognition Attendance**: Automated attendance marking using facial recognition
- **Real-time Webcam Integration**: Live camera feed for instant face detection
- **Admin Dashboard**: Comprehensive overview of attendance statistics
- **Employee Management**: Add, edit, and delete employee records with face registration
- **Detailed Reports**: Generate attendance reports with filtering and export capabilities
- **Email Notifications**: Automatic email alerts for attendance events

### Technical Features
- **Secure Authentication**: Admin login with password hashing
- **Database Management**: PostgreSQL with SQLAlchemy ORM
- **Face Recognition**: MTCNN for face detection + FaceNet for embeddings
- **Responsive UI**: Bootstrap 5.3 with modern design
- **CSV Export**: Download attendance reports in CSV format
- **Rate Limiting**: Protection against brute force attacks
- **Session Management**: Configurable session lifetime

## 🛠️ Technology Stack

### Backend
- **Flask 2.3.3**: Web framework
- **PostgreSQL**: Database
- **SQLAlchemy**: ORM
- **Flask-Login**: User authentication
- **Flask-Migrate**: Database migrations

### Face Recognition
- **OpenCV 4.8.0**: Image processing
- **MTCNN**: Face detection
- **FaceNet (PyTorch)**: Face embedding generation
- **NumPy**: Numerical computations

### Frontend
- **Bootstrap 5.3**: UI framework
- **jQuery**: JavaScript library
- **HTML5/CSS3**: Markup and styling

### Additional Libraries
- **Flask-Mail**: Email notifications
- **Flask-Limiter**: Rate limiting
- **Flask-WTF**: CSRF protection
- **Python-dotenv**: Environment management

## 📋 Prerequisites

Before running this application, ensure you have:

1. **Python 3.8+** installed
2. **PostgreSQL** database server running
3. **Webcam** for face recognition functionality
4. **Git** for version control

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd employee-attendance-system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Environment Configuration

Create a `.env` file in the root directory:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/attendance_system

# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=1

# Session Configuration
SESSION_LIFETIME_HOURS=8

# Face Recognition Settings
FACE_RECOGNITION_THRESHOLD=0.75
WORKING_HOURS_START=09:00
WORKING_HOURS_END=17:00
LATE_THRESHOLD_MINUTES=30

# Email Configuration (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

### 6. Database Setup

Create the PostgreSQL database:
```sql
CREATE DATABASE attendance_system;
```

### 7. Initialize Database

```bash
# Initialize database tables
flask init-db

# Create admin user
flask create-admin
```

### 8. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📁 Project Structure

```
employee-attendance-system/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── commands.py           # CLI commands
├── extensions.py         # Flask extensions
├── .env                  # Environment variables
├── models/               # Database models
│   ├── user.py          # User/Employee model
│   └── attendance.py    # Attendance model
├── templates/            # HTML templates
│   ├── base.html        # Base template
│   ├── index.html       # Home page
│   ├── login.html       # Login page
│   ├── admin_dashboard.html
│   ├── manage_employees.html
│   ├── employees.html
│   └── reports.html
├── static/              # Static files
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── utils/               # Utility functions
│   └── face_utils.py   # Face recognition utilities
└── migrations/          # Database migrations
```

## 🔧 Configuration

### Face Recognition Settings

- **FACE_RECOGNITION_THRESHOLD**: Similarity threshold for face matching (0.0-1.0)
- **WORKING_HOURS_START**: Start time for working hours (HH:MM)
- **WORKING_HOURS_END**: End time for working hours (HH:MM)
- **LATE_THRESHOLD_MINUTES**: Minutes after start time to mark as late

### Working Hours Configuration

The system automatically determines attendance status based on:
- **Present**: Clock-in before or at working hours start
- **Late**: Clock-in after working hours start but within late threshold
- **Absent**: No attendance recorded for the day

## 👥 User Roles

### Admin
- Access to admin dashboard
- Manage employees (add, edit, delete)
- View and export attendance reports
- Configure system settings

### Employee
- Mark attendance using face recognition
- View personal attendance history
- Receive email notifications

## 📊 Features Overview

### Admin Dashboard
- Real-time attendance statistics
- Employee count and present/late/absent numbers
- Recent attendance records
- Quick navigation to management functions

### Employee Management
- Add new employees with face registration
- Edit employee details and face data
- Delete employee records
- Department-based organization

### Attendance Reports
- Date range filtering
- Department-based filtering
- Summary statistics
- Detailed attendance records
- CSV export functionality

### Face Recognition System
- Real-time face detection
- High-accuracy face matching
- Automatic attendance marking
- Clock-in and clock-out functionality
- Minimum time requirements for clock-out

## 🔒 Security Features

- **Password Hashing**: Secure password storage using Werkzeug
- **CSRF Protection**: Cross-site request forgery protection
- **Rate Limiting**: Protection against brute force attacks
- **Session Management**: Configurable session lifetime
- **Input Validation**: Comprehensive input sanitization

## 📧 Email Notifications

The system sends automatic email notifications for:
- Successful clock-in events
- Successful clock-out events with hours worked
- Attendance status updates

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**: Ensure all sensitive data is in environment variables
2. **Database**: Use production-grade PostgreSQL setup
3. **Web Server**: Deploy with Gunicorn or uWSGI
4. **Reverse Proxy**: Use Nginx for static file serving
5. **SSL**: Enable HTTPS for secure communication
6. **Backup**: Implement regular database backups

### Docker Deployment (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

## 🧪 Testing

### Manual Testing
1. **Face Recognition**: Test with different lighting conditions
2. **Attendance Flow**: Verify clock-in/clock-out functionality
3. **Admin Functions**: Test employee management features
4. **Reports**: Verify data accuracy and export functionality

### Automated Testing (Future Enhancement)
- Unit tests for models and utilities
- Integration tests for API endpoints
- Face recognition accuracy testing

## 🔧 Troubleshooting

### Common Issues

1. **Face Recognition Not Working**
   - Ensure webcam permissions are granted
   - Check lighting conditions
   - Verify face is clearly visible

2. **Database Connection Issues**
   - Verify PostgreSQL is running
   - Check database credentials in `.env`
   - Ensure database exists

3. **Email Notifications Not Sending**
   - Verify email configuration in `.env`
   - Check SMTP server settings
   - Ensure app password is used for Gmail

### Performance Optimization

1. **Face Recognition**: Adjust threshold values for accuracy vs speed
2. **Database**: Add indexes for frequently queried columns
3. **Caching**: Implement Redis for session storage
4. **Image Processing**: Optimize image size and quality

## 📈 Future Enhancements

- **Mobile App**: Native mobile application
- **Biometric Integration**: Fingerprint and card reader support
- **Advanced Analytics**: Machine learning for attendance patterns
- **Multi-location Support**: Branch and location management
- **API Development**: RESTful API for third-party integrations
- **Real-time Notifications**: WebSocket-based live updates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

Created by Jagadeesh Lenka- A modern attendance management solution with face recognition technology.

## 🙏 Acknowledgments

- **MTCNN**: Face detection library
- **FaceNet**: Face recognition model
- **Flask**: Web framework
- **Bootstrap**: UI framework
- **OpenCV**: Computer vision library

---

**Note**: This system requires proper lighting conditions and clear face visibility for optimal face recognition performance. Regular maintenance of face data and system updates is recommended for continued accuracy. 