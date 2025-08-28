#!/bin/bash

echo "🚀 Starting Meshtastic Visualizer..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

echo ""
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "🔧 Initializing database..."
python3 -c "
import asyncio
from backend.database import Database

async def init():
    db = Database()
    await db.initialize()
    print('✅ Database initialized')

asyncio.run(init())
"

echo ""
echo "🎯 Starting backend server..."
# Start backend in background
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Backend running with PID: $BACKEND_PID"
echo ""

# Wait for backend to start
sleep 3

echo "🎨 Starting frontend development server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Frontend running with PID: $FRONTEND_PID"
echo ""
echo "✅ Meshtastic Visualizer is running!"
echo ""
echo "📱 Open your browser at: http://localhost:5173"
echo "🔌 Backend API available at: http://localhost:8000"
echo "📡 Make sure your RAK 4631 is connected via USB-C"
echo ""
echo "Press Ctrl+C to stop all services..."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "👋 Goodbye!"
    exit 0
}

# Set up trap to cleanup on Ctrl+C
trap cleanup INT

# Wait for processes
wait