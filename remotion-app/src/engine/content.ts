export const CURSOR_SFX = "cursor.mp3";
export const SCENE_OVERLAP = 10;
export const SFX = {
  pop: { src: "pop.mp3", volume: 1, durationInFrames: 10 },
  typing: { src: "typing.mp3", volume: 1, durationInFrames: 10 },
  notification: { src: "notif.mp3", volume: 1, durationInFrames: 10 }
};
export const TRANSITION_SFX = "transition.mp3";
export const SPREADSHEET_COLUMNS = ["Date", "Campaign", "Spend", "Status"];
export const SPREADSHEET_ROWS = [
  ["Oct 1", "Q4 Launch", "$1,200", "Active"],
  ["Oct 2", "Retargeting", "$800", "Pending"],
  ["Oct 3", "Brand", "$2,100", "Review"]
];
export const CHAT_MESSAGES = [
  { from: "Alex", text: "Did we launch the Q4 campaign yet?" },
  { from: "You", text: "Checking the spreadsheet now." }
];
export const EMAIL_THREAD = [
  { from: "billing@platform.com", subject: "Invoice #492", body: "Your account has been charged $1,200." },
  { from: "legal@corp.com", subject: "Action Required", body: "Please review the updated terms of service." }
];
export const NOTIFICATIONS = [
  { title: "Server Alert", body: "High CPU usage detected." },
  { title: "Deployment Failed", body: "Build #1042 failed in CI." }
];
export const STICKY_NOTES = [
  { text: "Call Sarah at 3PM", color: "#FDFD96" },
  { text: "Fix layout bug!!", color: "#FFB7B2" },
  { text: "Don't forget to push", color: "#B5EAD7" }
];
