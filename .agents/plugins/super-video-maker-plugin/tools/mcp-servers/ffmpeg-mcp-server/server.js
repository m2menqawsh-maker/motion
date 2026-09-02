#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import { exec, spawn } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import fsSync from 'fs';
import path from 'path';
import crypto from 'crypto';

const execAsync = promisify(exec);

import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKSPACE_ROOT = path.resolve(__dirname, '../../..');

// MCP State Directory
const STATE_DIR = path.join(WORKSPACE_ROOT, '.agents', 'mcp_state');
const STATE_FILE = path.join(STATE_DIR, 'ffmpeg_jobs.json');

// Ensure state directory exists synchronously on startup
if (!fsSync.existsSync(STATE_DIR)) {
  fsSync.mkdirSync(STATE_DIR, { recursive: true });
}

// Helper: Atomic JSON Write
async function saveStateAtomically(data) {
  const tempFile = `${STATE_FILE}.${crypto.randomBytes(4).toString('hex')}.tmp`;
  try {
    await fs.writeFile(tempFile, JSON.stringify(data, null, 2), 'utf8');
    await fs.rename(tempFile, STATE_FILE);
  } catch (err) {
    console.error(`[State Error] Failed to save state atomically: ${err.message}`);
    if (fsSync.existsSync(tempFile)) {
      try { fsSync.unlinkSync(tempFile); } catch (e) {}
    }
  }
}

// Helper: Read State
async function readState() {
  try {
    const data = await fs.readFile(STATE_FILE, 'utf8');
    return JSON.parse(data);
  } catch (err) {
    if (err.code !== 'ENOENT') {
      console.error(`[State Error] Failed to read state: ${err.message}`);
    }
    return {};
  }
}

// Helper: Check running FFmpeg processes via WMI
async function getRunningFFmpegProcesses() {
  try {
    const { stdout } = await execAsync('powershell -NoProfile -Command "Get-WmiObject Win32_Process | Where-Object { $_.Name -match \'ffmpeg\' } | Select-Object ProcessId, CommandLine | ConvertTo-Json"');
    if (!stdout.trim()) return [];
    const parsed = JSON.parse(stdout);
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch (err) {
    console.error(`[WMI Error] Failed to get running FFmpeg processes: ${err.message}`);
    return [];
  }
}

class FFmpegMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'ffmpeg-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Track background processing operations
    this.processingQueue = new Map();
    this.serverId = crypto.randomUUID();
    this.setupToolHandlers();
    
    // Asynchronously restore state
    this.restoreState().catch(err => console.error(`[State Error] Restore failed: ${err.message}`));
  }

  async restoreState() {
    const persistedJobs = await readState();
    const runningFFmpeg = await getRunningFFmpegProcesses();
    
    let stateChanged = false;
    for (const [jobId, job] of Object.entries(persistedJobs)) {
      if (job.status === 'processing' || job.status === 'orphaned') {
        // Verify if the job is still running by checking WMI ProcessId and CommandLine
        const matchingProcess = runningFFmpeg.find(p => p.ProcessId === job.pid);
        
        // Anti-spoofing / verification check
        if (matchingProcess && matchingProcess.CommandLine && matchingProcess.CommandLine.includes('ffmpeg') && matchingProcess.CommandLine.includes(path.basename(job.outputFile))) {
          job.status = 'orphaned';
          console.error(`[Recovery] [ORPHAN_DETECTED] Adopted orphaned FFmpeg process ${job.pid} for job ${jobId}`);
          stateChanged = true;
        } else {
          if (matchingProcess) {
            console.error(`[Recovery] [PID_MISMATCH] PID ${job.pid} exists but does not match expected FFmpeg job ${jobId}`);
          }
          job.status = 'unknown'; // Interrupted and no longer running
          job.error = 'MCP Server restarted. Underlying process could not be found or verified.';
          job.endTime = new Date().toISOString();
          console.error(`[Recovery] [JOB_FAILED] Job ${jobId} marked as UNKNOWN (Process lost)`);
          stateChanged = true;
        }
      }
      this.processingQueue.set(jobId, job);
    }
    if (stateChanged) {
      this.persistState();
    }
    console.error(`[MCP_SERVER_RESTART_RECOVERY] Restored ${Object.keys(persistedJobs).length} jobs from state.`);
  }

  persistState() {
    saveStateAtomically(Object.fromEntries(this.processingQueue)).catch(() => {});
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'speed_up_video',
            description: 'Speed up a video by a given factor (e.g., 50 = 50x faster). For large files, processing starts in background.',
            inputSchema: {
              type: 'object',
              properties: {
                filename: {
                  type: 'string',
                  description: 'Name of the video file (e.g., "GX010412.MP4"). The file will be searched in the configured folder.'
                },
                speed_factor: {
                  type: 'number',
                  minimum: 1,
                  maximum: 1000,
                  description: 'Speed multiplier (e.g., 50 = 50x faster)'
                },
                output_suffix: {
                  type: 'string',
                  description: 'Optional suffix for output filename (defaults to "x{speed_factor}")',
                  default: ''
                }
              },
              required: ['filename', 'speed_factor']
            }
          },
          {
            name: 'check_processing_status',
            description: 'Check the status of background video processing operations.',
            inputSchema: {
              type: 'object',
              properties: {},
              required: []
            }
          },
          {
            name: 'cancel_video_processing',
            description: 'Cancel an active FFmpeg video processing job.',
            inputSchema: {
              type: 'object',
              properties: {
                jobId: { type: 'string', description: 'The Job ID to cancel' }
              },
              required: ['jobId']
            }
          },
          {
            name: 'increase_keyframes',
            description: 'Increase the number of keyframes in a video by setting GOP (Group of Pictures) value. Lower GOP = more keyframes.',
            inputSchema: {
              type: 'object',
              properties: {
                filename: {
                  type: 'string',
                  description: 'Name of the video file (e.g., "input.mp4"). The file will be searched in the configured folder.'
                },
                gop_value: {
                  type: 'number',
                  minimum: 1,
                  maximum: 300,
                  description: 'GOP (Group of Pictures) value. 1 = keyframe every frame, 30 = keyframe every 30th frame'
                },
                output_suffix: {
                  type: 'string',
                  description: 'Optional suffix for output filename (defaults to "_gop{gop_value}")',
                  default: ''
                }
              },
              required: ['filename', 'gop_value']
            }
          },
          {
            name: 'get_files_info',
            description: 'Get a list of all files in the configured video folder with their names and modification dates.',
            inputSchema: {
              type: 'object',
              properties: {
                directory: {
                  type: 'string',
                  description: 'The directory to read files from. Must be an explicit path.'
                }
              },
              required: ['directory']
            }
          },
          {
            name: 'concatenate_videos',
            description: 'Concatenate multiple video files into one output video. Creates temporary text file, processes videos, and cleans up automatically.',
            inputSchema: {
              type: 'object',
              properties: {
                video_files: {
                  type: 'array',
                  items: { type: 'string' },
                  description: 'Array of video filenames to concatenate in order (e.g., ["GX010410x50.MP4", "GX010419x50.MP4"])'
                },
                output_filename: {
                  type: 'string',
                  description: 'Name for the output concatenated video file (e.g., "concatenated_output.mp4")'
                }
              },
              required: ['video_files', 'output_filename']
            }
          }
        ]
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      try {
        switch (name) {
          case "speed_up_video":
            return await this.speedUpVideo(args);
          case "check_processing_status":
            return await this.checkProcessingStatus(args);
          case "cancel_video_processing":
            return await this.cancelVideoProcessing(args);
          case "increase_keyframes":
            return await this.increaseKeyframes(args);
          case "get_files_info":
            return await this.getFilesInfo(args);
          case "concatenate_videos":
            return await this.concatenateVideos(args);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`
            );
        }
      } catch (error) {
        throw new McpError(
          ErrorCode.InternalError,
          `Tool execution failed: ${error.message}`
        );
      }
    });
  }

  async speedUpVideo(args) {
    const { filename, speed_factor, output_suffix } = args;
    const baseFolder = process.env.VIDEOS_PATH || process.env.VIDEO_FOLDER || '.';
    const inputPath = path.resolve(baseFolder, filename);
    
    const fileExt = path.extname(filename);
    const baseName = path.basename(filename, fileExt);
    const suffix = output_suffix || `x${speed_factor}`;
    const outputFilename = `${baseName}${suffix}${fileExt}`;
    const outputPath = path.join(baseFolder, outputFilename);
    
    let fileStats;
    try {
      fileStats = await fs.stat(inputPath);
    } catch (error) {
      throw new Error(`Input file not found: ${inputPath}`);
    }
    const fileSizeGB = fileStats.size / (1024 * 1024 * 1024);
    const ptsValue = (1 / speed_factor).toFixed(4);
    
    const commandArgs = ['-y', '-i', inputPath, '-filter:v', `setpts=${ptsValue}*PTS`, '-r', '30', '-an', '-c:v', 'mpeg4', '-q:v', '5', outputPath];
    
    const jobId = `${baseName}_${Date.now()}`;
    
    console.error(`[JOB_CREATED] Starting speed_up_video for file (${fileSizeGB.toFixed(2)}GB) with job ID: ${jobId}`);
    
    const jobData = {
      serverId: this.serverId,
      status: 'pending',
      inputFile: filename,
      outputFile: outputFilename,
      startTime: new Date().toISOString(),
      command: commandArgs.join(' '),
      fileSize: fileSizeGB
    };
    
    this.processingQueue.set(jobId, jobData);
    this.persistState();
    
    this.startBackgroundProcessing(jobId, commandArgs, inputPath, outputPath);
    
    return {
      content: [
        {
          type: "text",
          text: `Started processing video (${fileSizeGB.toFixed(2)}GB).\nJob ID: ${jobId}\nInput: ${inputPath}\nOutput: ${outputPath}\nSpeed: ${speed_factor}x (PTS: ${ptsValue})\nEstimated time: ${this.estimateProcessingTime(fileSizeGB, speed_factor)}\n\nProcessing in background. Use 'check_processing_status' to monitor progress.`
        }
      ]
    };
  }

  async getFilesInfo(args) {
    const baseFolder = (args && args.directory) || process.env.VIDEOS_PATH || process.env.VIDEO_FOLDER;
    if (!baseFolder || baseFolder === '.') {
      throw new Error("No directory provided. You must explicitly provide a 'directory' argument.");
    }
    
    try {
      await fs.access(baseFolder);
      const files = await fs.readdir(baseFolder);
      const filesInfo = [];
      
      for (const filename of files) {
        const filePath = path.join(baseFolder, filename);
        try {
          const stats = await fs.stat(filePath);
          if (stats.isFile()) {
            filesInfo.push({
              name: filename,
              size: stats.size,
              modified: stats.mtime.toISOString(),
              sizeReadable: this.formatFileSize(stats.size)
            });
          }
        } catch (statError) {
          console.error(`Could not get stats for file: ${filename}`);
        }
      }
      
      filesInfo.sort((a, b) => new Date(b.modified) - new Date(a.modified));
      const filesList = filesInfo.map(file => 
        `${file.name} (${file.sizeReadable}, modified: ${new Date(file.modified).toLocaleString()})`
      ).join('\n');
      
      return {
        content: [
          {
            type: "text",
            text: `Files in ${baseFolder}:\n\nTotal files: ${filesInfo.length}\n\n${filesList || 'No files found.'}`
          }
        ]
      };
    } catch (error) {
      throw new Error(`Failed to read directory: ${error.message}`);
    }
  }

  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  async concatenateVideos(args) {
    const { video_files, output_filename } = args;
    const baseFolder = process.env.VIDEOS_PATH || process.env.VIDEO_FOLDER || '.';
    
    const tempListFile = `concat_list.txt`;
    const tempListPath = path.join(baseFolder, tempListFile);
    const outputPath = path.join(baseFolder, output_filename);
    
    try {
      for (const filename of video_files) {
        const inputPath = path.join(baseFolder, filename);
        try {
          await fs.access(inputPath);
        } catch (error) {
          throw new Error(`Input video file not found: ${inputPath}`);
        }
      }
      
      const listContent = video_files.map(filename => `file '${filename}'`).join('\n');
      await fs.writeFile(tempListPath, listContent, 'utf8');
      
      const command = `ffmpeg -f concat -safe 0 -i ${tempListFile} -c copy ${output_filename}`;
      await execAsync(command, { cwd: baseFolder });
      
      await fs.unlink(tempListPath);
      
      return {
        content: [
          {
            type: "text",
            text: `Successfully concatenated ${video_files.length} videos.\nInput videos: ${video_files.join(', ')}\nOutput: ${outputPath}\nTemporary list file cleaned up.`
          }
        ]
      };
    } catch (error) {
      try {
        await fs.unlink(tempListPath);
      } catch (unlinkError) {}
      throw new Error(`FFmpeg concatenation failed: ${error.message}`);
    }
  }

  async increaseKeyframes(args) {
    const { filename, gop_value, output_suffix } = args;
    const baseFolder = process.env.VIDEOS_PATH || process.env.VIDEO_FOLDER || '.';
    
    const inputPath = path.resolve(baseFolder, filename);
    const fileExt = path.extname(filename);
    const baseName = path.basename(filename, fileExt);
    const suffix = output_suffix || `_gop${gop_value}`;
    const outputFilename = `${baseName}${suffix}${fileExt}`;
    const outputPath = path.join(baseFolder, outputFilename);
    
    let fileStats;
    try {
      fileStats = await fs.stat(inputPath);
    } catch (error) {
      throw new Error(`Input file not found: ${inputPath}`);
    }
    
    const fileSizeGB = fileStats.size / (1024 * 1024 * 1024);
    const commandArgs = ['-y', '-i', inputPath, '-c:v', 'libx264', '-g', gop_value.toString(), '-c:a', 'copy', outputPath];
    
    const jobId = `${baseName}_keyframes_${Date.now()}`;
    
    console.error(`[JOB_CREATED] Starting increaseKeyframes for file (${fileSizeGB.toFixed(2)}GB) with job ID: ${jobId}`);
    
    const jobData = {
      serverId: this.serverId,
      status: 'pending',
      inputFile: filename,
      outputFile: outputFilename,
      startTime: new Date().toISOString(),
      command: commandArgs.join(' '),
      fileSize: fileSizeGB
    };
    
    this.processingQueue.set(jobId, jobData);
    this.persistState();
    
    this.startBackgroundProcessing(jobId, commandArgs, inputPath, outputPath);
    
    return {
      content: [
        {
          type: "text",
          text: `Started keyframe processing (${fileSizeGB.toFixed(2)}GB).\nJob ID: ${jobId}\nInput: ${inputPath}\nOutput: ${outputPath}\nGOP value: ${gop_value} (keyframe every ${gop_value} frame${gop_value !== 1 ? 's' : ''})\nEstimated time: ${this.estimateProcessingTime(fileSizeGB, 1)}\n\nProcessing in background. Use 'check_processing_status' to monitor progress.`
        }
      ]
    };
  }

  startBackgroundProcessing(jobId, commandArgs, inputPath, outputPath) {
    console.error(`[JOB_STARTED] Starting background job ${jobId}`);
    
    const job = this.processingQueue.get(jobId);
    if (!job) return;

    job.status = 'processing';
    
    const logPath = path.join(STATE_DIR, `${jobId}.log`);
    const outFd = fsSync.openSync(logPath, 'a');
    
    const child = spawn('ffmpeg', commandArgs, {
      detached: true,
      stdio: ['ignore', 'ignore', outFd],
      windowsHide: true,
      cwd: path.dirname(inputPath)
    });
    
    job.pid = child.pid;
    this.persistState();
    console.error(`[JOB_PERSISTED] Job ${jobId} saved with PID ${child.pid}`);
    
    child.on('exit', (code) => {
      try { fsSync.closeSync(outFd); } catch(e) {}
      
      const currentJob = this.processingQueue.get(jobId);
      if (!currentJob) return;
      
      if (currentJob.status === 'cancelled') return;
      
      if (code === 0) {
        console.error(`[JOB_COMPLETED] Background job ${jobId} completed successfully`);
        currentJob.status = 'completed';
      } else {
        console.error(`[JOB_FAILED] Background job ${jobId} failed with exit code ${code}`);
        currentJob.status = 'failed';
        currentJob.error = `Exited with code ${code}`;
      }
      currentJob.endTime = new Date().toISOString();
      this.persistState();
    });
    
    child.unref();
  }

  async cancelVideoProcessing(args) {
    const { jobId } = args;
    const job = this.processingQueue.get(jobId);
    
    if (!job) {
      throw new Error(`Job ${jobId} not found`);
    }
    
    if (job.status !== 'processing' && job.status !== 'orphaned') {
      throw new Error(`Job ${jobId} is not active (status: ${job.status})`);
    }
    
    const runningFFmpeg = await getRunningFFmpegProcesses();
    const matchingProcess = runningFFmpeg.find(p => p.ProcessId === job.pid && p.CommandLine && p.CommandLine.includes('ffmpeg'));
    
    if (matchingProcess) {
      console.error(`[JOB_CANCELLED] Cancelling job ${jobId}, killing verified PID ${job.pid}`);
      try {
        await execAsync(`taskkill /F /PID ${job.pid}`);
      } catch (e) {
        console.error(`Failed to taskkill PID ${job.pid}: ${e.message}`);
        // Fallback
        try { process.kill(job.pid, 'SIGKILL'); } catch (e2) {}
      }
    } else {
      console.error(`[JOB_CANCELLED] Job ${jobId} PID ${job.pid} not found in WMI during cancel`);
    }
    
    job.status = 'cancelled';
    job.endTime = new Date().toISOString();
    this.persistState();
    
    return {
      content: [{ type: "text", text: `Job ${jobId} cancelled successfully.` }]
    };
  }

  async checkProcessingStatus(args) {
    // Proactively verify running/orphaned jobs
    const runningFFmpeg = await getRunningFFmpegProcesses();
    let stateChanged = false;
    
    for (const [jobId, job] of this.processingQueue.entries()) {
      if (job.status === 'processing' || job.status === 'orphaned') {
        const matchingProcess = runningFFmpeg.find(p => p.ProcessId === job.pid && p.CommandLine && p.CommandLine.includes('ffmpeg'));
        
        if (!matchingProcess) {
          // Process has ended, and we missed the 'exit' event (or it was an orphan).
          // We check the log file to determine if it completed successfully.
          const logPath = path.join(STATE_DIR, `${jobId}.log`);
          let success = false;
          try {
            const logData = await fs.readFile(logPath, 'utf8');
            // 'Qavg:' or 'muxing overhead' indicates normal termination for most encoding
            if (logData.includes('muxing overhead') || logData.includes('Qavg')) {
              success = true;
            }
          } catch(e) {}
          
          if (success) {
            console.error(`[JOB_COMPLETED] Orphaned job ${jobId} finished successfully`);
            job.status = 'completed';
          } else {
            console.error(`[JOB_FAILED] Orphaned job ${jobId} finished with unknown state / partial error`);
            job.status = 'unknown'; // Unknown because we couldn't verify exit code 0
            job.error = 'Process ended. Completion could not be reliably verified via logs.';
          }
          job.endTime = new Date().toISOString();
          stateChanged = true;
        }
      }
    }
    
    if (stateChanged) {
      this.persistState();
    }

    const jobs = Array.from(this.processingQueue.entries()).map(([jobId, job]) => {
      const duration = job.endTime 
        ? (new Date(job.endTime) - new Date(job.startTime)) / 1000 
        : (new Date() - new Date(job.startTime)) / 1000;
      
      return {
        jobId,
        status: job.status,
        inputFile: job.inputFile,
        outputFile: job.outputFile,
        fileSize: `${job.fileSize.toFixed(2)}GB`,
        duration: `${Math.floor(duration)}s`,
        startTime: new Date(job.startTime).toLocaleString(),
        endTime: job.endTime ? new Date(job.endTime).toLocaleString() : null,
        error: job.error || null
      };
    });
    
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    for (const [jobId, job] of this.processingQueue.entries()) {
      if ((job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled' || job.status === 'unknown') && 
          job.endTime && new Date(job.endTime) < oneHourAgo) {
        this.processingQueue.delete(jobId);
      }
    }
    
    const activeJobs = jobs.filter(job => job.status === 'processing' || job.status === 'orphaned');
    const completedJobs = jobs.filter(job => job.status === 'completed');
    const failedJobs = jobs.filter(job => job.status === 'failed' || job.status === 'unknown' || job.status === 'cancelled');
    
    let statusText = `Processing Status Summary:\n\n`;
    statusText += `Active/Orphaned jobs: ${activeJobs.length}\n`;
    statusText += `Completed jobs: ${completedJobs.length}\n`;
    statusText += `Failed/Unknown/Cancelled jobs: ${failedJobs.length}\n\n`;
    
    if (activeJobs.length > 0) {
      statusText += `ACTIVE JOBS:\n`;
      activeJobs.forEach(job => {
        statusText += `• [${job.status.toUpperCase()}] ${job.jobId}: ${job.inputFile} (${job.fileSize}) - Running for ${job.duration}\n`;
      });
      statusText += `\n`;
    }
    
    if (completedJobs.length > 0) {
      statusText += `RECENTLY COMPLETED:\n`;
      completedJobs.slice(-3).forEach(job => {
        statusText += `• ${job.outputFile} - Completed in ${job.duration} (${job.endTime})\n`;
      });
      statusText += `\n`;
    }
    
    if (failedJobs.length > 0) {
      statusText += `FAILED/UNKNOWN/CANCELLED JOBS:\n`;
      failedJobs.slice(-3).forEach(job => {
        statusText += `• [${job.status.toUpperCase()}] ${job.inputFile} - Ended after ${job.duration}: ${job.error || 'N/A'}\n`;
      });
    }
    
    if (jobs.length === 0) {
      statusText += `No recent processing jobs found.`;
    }
    
    return {
      content: [
        {
          type: "text",
          text: statusText
        }
      ]
    };
  }

  estimateProcessingTime(fileSizeGB, speedFactor) {
    const baseMinutesPerGB = 3;
    const estimatedMinutes = fileSizeGB * baseMinutesPerGB;
    
    if (estimatedMinutes < 60) {
      return `~${Math.ceil(estimatedMinutes)} minutes`;
    } else {
      const hours = Math.floor(estimatedMinutes / 60);
      const minutes = Math.ceil(estimatedMinutes % 60);
      return `~${hours}h ${minutes}m`;
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("FFmpeg MCP server running on stdio");
  }
}

const server = new FFmpegMCPServer();
server.run().catch(console.error);
