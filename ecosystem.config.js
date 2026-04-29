/**
 * PM2 Ecosystem Configuration — Platinum Tier
 * Manages all AI Employee processes with auto-restart on crash.
 *
 * Usage:
 *   pm2 start ecosystem.config.js        # start all
 *   pm2 restart all                       # restart all
 *   pm2 status                            # view status
 *   pm2 logs                              # view logs
 *   pm2 save && pm2 startup               # persist across reboots
 */

module.exports = {
  apps: [
    // ── Cloud Agent (24/7 on VM) ──────────────────────────────
    {
      name: "cloud_watcher",
      script: "cloud/cloud_watcher.py",
      interpreter: "python",
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,         // 5s between restarts
      max_memory_restart: "300M",
      env: {
        PYTHONUNBUFFERED: "1",
        AGENT_MODE: "cloud",
      },
      log_file: "Logs/pm2_cloud_watcher.log",
      error_file: "Logs/pm2_cloud_watcher_error.log",
      time: true,
    },

    // ── Scheduler (cron jobs) ─────────────────────────────────
    {
      name: "scheduler",
      script: "scheduler.py",
      interpreter: "python",
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      max_memory_restart: "200M",
      env: {
        PYTHONUNBUFFERED: "1",
      },
      log_file: "Logs/pm2_scheduler.log",
      error_file: "Logs/pm2_scheduler_error.log",
      time: true,
    },

    // ── Vault Sync (Git push/pull loop) ───────────────────────
    {
      name: "vault_sync",
      script: "vault_sync.py",
      interpreter: "python",
      args: "--watch",
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_restarts: 5,
      restart_delay: 10000,       // 10s between restarts
      max_memory_restart: "150M",
      env: {
        PYTHONUNBUFFERED: "1",
        SYNC_INTERVAL: "60",
      },
      log_file: "Logs/pm2_vault_sync.log",
      error_file: "Logs/pm2_vault_sync_error.log",
      time: true,
    },

    // ── Health Monitor (every 5 min) ──────────────────────────
    {
      name: "health_monitor",
      script: "health_monitor.py",
      interpreter: "python",
      args: "--watch",
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      max_memory_restart: "100M",
      env: {
        PYTHONUNBUFFERED: "1",
      },
      log_file: "Logs/pm2_health_monitor.log",
      error_file: "Logs/pm2_health_monitor_error.log",
      time: true,
    },

    // ── Approval Watcher (Local only) ─────────────────────────
    {
      name: "approval_watcher",
      script: "approval_watcher.py",
      interpreter: "python",
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      max_memory_restart: "150M",
      env: {
        PYTHONUNBUFFERED: "1",
        AGENT_MODE: "local",
      },
      log_file: "Logs/pm2_approval_watcher.log",
      error_file: "Logs/pm2_approval_watcher_error.log",
      time: true,
    },

    // ── Gmail Watcher ─────────────────────────────────────────
    {
      name: "gmail_watcher",
      script: "gmail_watcher.py",
      interpreter: "python",
      cwd: __dirname,
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 10000,
      max_memory_restart: "200M",
      env: {
        PYTHONUNBUFFERED: "1",
      },
      log_file: "Logs/pm2_gmail_watcher.log",
      error_file: "Logs/pm2_gmail_watcher_error.log",
      time: true,
    },

    // ── Queue Processor (retry failed tasks) ──────────────────
    {
      name: "queue_processor",
      script: "retry_handler.py",
      interpreter: "python",
      args: "--process-queue",
      cwd: __dirname,
      watch: false,
      autorestart: false,          // one-shot, triggered by cron
      cron_restart: "*/15 * * * *", // every 15 minutes
      env: {
        PYTHONUNBUFFERED: "1",
      },
      log_file: "Logs/pm2_queue_processor.log",
      error_file: "Logs/pm2_queue_processor_error.log",
      time: true,
    },
  ],
};
