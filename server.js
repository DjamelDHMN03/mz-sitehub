const { spawn } = require('child_process');
const path = require('path');

const backendDir = path.join(__dirname, 'backend');
const frontendDir = path.join(__dirname, 'frontend');

// Lancer le Backend FastAPI directement depuis le dossier backend
const backend = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], {
  cwd: backendDir,
  env: { ...process.env, PYTHONPATH: backendDir },
  shell: true,
  stdio: 'inherit'
});

// Lancer le Frontend Vite/React
const frontend = spawn('npm', ['run', 'dev'], {
  cwd: frontendDir,
  shell: true,
  stdio: 'inherit'
});

process.on('SIGINT', () => {
  backend.kill();
  frontend.kill();
  process.exit(0);
});