module.exports = {
  apps: [
    {
      name: "mz-sitehub-app",
      script: "./server.js",
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      watch: false
    }
  ]
};