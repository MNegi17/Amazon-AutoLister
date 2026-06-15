"use client";

import React, { useState, useEffect } from "react";
import { 
  LayoutDashboard, 
  UploadCloud, 
  BrainCircuit, 
  FileSpreadsheet, 
  Settings, 
  Download, 
  Play, 
  Trash2, 
  ToggleLeft, 
  ToggleRight, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  FileText, 
  Plus, 
  HelpCircle,
  RefreshCw
} from "lucide-react";

// Get API URL from env or localStorage dynamically
let API_URL = "http://localhost:8001";
if (typeof window !== "undefined") {
  const savedUrl = localStorage.getItem("API_URL");
  const defaultUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
  API_URL = savedUrl || defaultUrl;
}

export default function Home() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [currentApiUrl, setCurrentApiUrl] = useState(API_URL);
  const [files, setFiles] = useState<any>({
    item_directory: [],
    master_sheet: [],
    content_sheet: [],
    amazon_template: [],
    historical_listing: []
  });
  const [mappings, setMappings] = useState<any>({ column_mappings: [], value_mappings: [] });
  const [rules, setRules] = useState<any>([]);
  const [defaults, setDefaults] = useState<any>({});
  const [tasks, setTasks] = useState<any>([]);
  
  // Selection states for generation
  const [selectedDir, setSelectedDir] = useState("");
  const [selectedMaster, setSelectedMaster] = useState("");
  const [selectedContent, setSelectedContent] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [skusInput, setSkusInput] = useState("");
  const [currentTaskId, setCurrentTaskId] = useState("");
  const [taskDetail, setTaskDetail] = useState<any>(null);
  
  // Settings edit states
  const [newDefaultAttr, setNewDefaultAttr] = useState("");
  const [newDefaultVal, setNewDefaultVal] = useState("");
  const [newRuleScope, setNewRuleScope] = useState("global");
  const [newRuleScopeVal, setNewRuleScopeVal] = useState("");
  const [newRuleAttr, setNewRuleAttr] = useState("");
  const [newRuleVal, setNewRuleVal] = useState("");

  // Loading states
  const [loading, setLoading] = useState({
    files: false,
    mappings: false,
    rules: false,
    defaults: false,
    tasks: false,
    generate: false,
    train: false
  });

  // Fetch all initial data
  const fetchData = async () => {
    setLoading((prev: any) => ({ ...prev, files: true, mappings: true, rules: true, defaults: true, tasks: true }));
    
    try {
      // 1. Files
      const filesRes = await fetch(`${API_URL}/api/files`);
      if (filesRes.ok) setFiles(await filesRes.json());
      
      // 2. Mappings
      const mappingsRes = await fetch(`${API_URL}/api/mappings`);
      if (mappingsRes.ok) setMappings(await mappingsRes.json());
      
      // 3. Rules
      const rulesRes = await fetch(`${API_URL}/api/settings/rules`);
      if (rulesRes.ok) setRules(await rulesRes.json());
      
      // 4. Defaults
      const defaultsRes = await fetch(`${API_URL}/api/settings/defaults`);
      if (defaultsRes.ok) setDefaults(await defaultsRes.json());
      
      // 5. Tasks
      const tasksRes = await fetch(`${API_URL}/api/tasks`);
      if (tasksRes.ok) setTasks(await tasksRes.json());
    } catch (err) {
      console.error("Error fetching data from API:", err);
    } finally {
      setLoading((prev: any) => ({ ...prev, files: false, mappings: false, rules: false, defaults: false, tasks: false }));
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Poll task status if active task is running
  useEffect(() => {
    let interval: any;
    if (currentTaskId) {
      const fetchTaskStatus = async () => {
        try {
          const res = await fetch(`${API_URL}/api/tasks/${currentTaskId}`);
          if (res.ok) {
            const data = await res.json();
            setTaskDetail(data);
            if (data.status === "completed" || data.status === "failed") {
              setCurrentTaskId(""); // Stop polling
              fetchData(); // Refresh tasks list
            }
          }
        } catch (err) {
          console.error("Error polling task:", err);
        }
      };
      
      fetchTaskStatus();
      interval = setInterval(fetchTaskStatus, 2000);
    }
    return () => clearInterval(interval);
  }, [currentTaskId]);

  // File Upload handler
  const handleFileUpload = async (e: any, fileType: string) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", fileType);
    
    try {
      const res = await fetch(`${API_URL}/api/upload`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        const newIdStr = data.id.toString();
        if (fileType === "item_directory") {
          setSelectedDir(newIdStr);
          setSelectedMaster(newIdStr);
        } else if (fileType === "content_sheet") {
          setSelectedContent(newIdStr);
        } else if (fileType === "amazon_template") {
          setSelectedTemplate(newIdStr);
        }
        fetchData();
      } else {
        alert("Upload failed.");
      }
    } catch (err) {
      console.error(err);
      alert("Error uploading file.");
    }
  };

  // Delete file handler
  const handleDeleteFile = async (id: any) => {
    if (!confirm("Are you sure you want to delete this file?")) return;
    try {
      const res = await fetch(`${API_URL}/api/files/${id}`, { method: "DELETE" });
      if (res.ok) {
        const idStr = id.toString();
        if (selectedDir === idStr) {
          setSelectedDir("");
          setSelectedMaster("");
        }
        if (selectedContent === idStr) {
          setSelectedContent("");
        }
        if (selectedTemplate === idStr) {
          setSelectedTemplate("");
        }
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Toggle column mapping state
  const handleToggleColumn = async (id: any) => {
    try {
      const res = await fetch(`${API_URL}/api/mappings/column/${id}/toggle`, { method: "POST" });
      if (res.ok) {
        // Update state locally
        setMappings((prev: any) => ({
          ...prev,
          column_mappings: prev.column_mappings.map((m: any) => m.id === id ? { ...m, is_active: !m.is_active } : m)
        }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Delete value mapping
  const handleDeleteValueMapping = async (id: any) => {
    try {
      const res = await fetch(`${API_URL}/api/mappings/value/${id}`, { method: "DELETE" });
      if (res.ok) {
        setMappings((prev: any) => ({
          ...prev,
          value_mappings: prev.value_mappings.filter((v: any) => v.id !== id)
        }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Add custom default
  const handleAddDefault = async () => {
    if (!newDefaultAttr || !newDefaultVal) return;
    const newDefaults = { ...defaults, [newDefaultAttr.trim()]: newDefaultVal.trim() };
    try {
      const res = await fetch(`${API_URL}/api/settings/defaults`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newDefaults)
      });
      if (res.ok) {
        setDefaults(newDefaults);
        setNewDefaultAttr("");
        setNewDefaultVal("");
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Delete default
  const handleDeleteDefault = async (attr: any) => {
    const newDefaults = { ...defaults };
    delete newDefaults[attr];
    try {
      const res = await fetch(`${API_URL}/api/settings/defaults`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newDefaults)
      });
      if (res.ok) setDefaults(newDefaults);
    } catch (err) {
      console.error(err);
    }
  };

  // Add rule
  const handleAddRule = async () => {
    if (!newRuleAttr || !newRuleVal) return;
    const formData = new FormData();
    formData.append("scope", newRuleScope);
    formData.append("scope_value", newRuleScopeVal);
    formData.append("amazon_attribute", newRuleAttr);
    formData.append("rule_value", newRuleVal);
    
    try {
      const res = await fetch(`${API_URL}/api/settings/rules`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        fetchData();
        setNewRuleAttr("");
        setNewRuleVal("");
        setNewRuleScopeVal("");
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Delete rule
  const handleDeleteRule = async (id: any) => {
    try {
      const res = await fetch(`${API_URL}/api/settings/rules/${id}`, { method: "DELETE" });
      if (res.ok) fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  // Train AI mapping on historical listings
  const handleTrainEngine = async (historyId: any) => {
    setLoading((prev: any) => ({ ...prev, train: true }));
    const formData = new FormData();
    formData.append("history_id", historyId);
    if (files.item_directory.length > 0) formData.append("directory_id", files.item_directory[0].id);
    if (files.master_sheet.length > 0) formData.append("master_id", files.master_sheet[0].id);
    if (files.content_sheet.length > 0) formData.append("content_id", files.content_sheet[0].id);
    
    try {
      const res = await fetch(`${API_URL}/api/train`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        alert("Training started in the background. Refresh mappings shortly!");
        fetchData();
      } else {
        alert("Training failed to start.");
      }
    } catch (err) {
      console.error(err);
      alert("Error running training.");
    } finally {
      setLoading((prev: any) => ({ ...prev, train: false }));
    }
  };

  // Generate Listing
  const handleGenerateListings = async () => {
    if (!skusInput.trim()) {
      alert("Please enter SKUs to generate.");
      return;
    }
    if (!selectedDir || !selectedContent || !selectedTemplate) {
      alert("Please upload and select all required source files and template.");
      return;
    }
    
    setLoading((prev: any) => ({ ...prev, generate: true }));
    
    const formData = new FormData();
    formData.append("skus_input", skusInput);
    formData.append("directory_id", selectedDir);
    formData.append("master_id", selectedDir); // Item Directory and Master Sheet are the same
    formData.append("content_id", selectedContent);
    formData.append("template_id", selectedTemplate);
    
    try {
      const res = await fetch(`${API_URL}/api/generate`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentTaskId(data.task_id);
        setActiveTab("logs"); // Switch to live logs tab
      } else {
        alert("Generation failed to start.");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading((prev: any) => ({ ...prev, generate: false }));
    }
  };

  // Handle File Download
  const handleDownload = async (taskId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/tasks/${taskId}/download`);
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Amazon_Listing_${taskId}.xlsm`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading file:", err);
      alert("Failed to download file. Please try again.");
    }
  };

  const handleUpdateApiUrl = () => {
    const newUrl = prompt("Enter Backend API URL (e.g., https://backend-production.up.railway.app):", currentApiUrl);
    if (newUrl) {
      const trimmed = newUrl.trim().replace(/\/$/, "");
      localStorage.setItem("API_URL", trimmed);
      API_URL = trimmed;
      setCurrentApiUrl(trimmed);
      // Reload data with new URL
      setTimeout(() => fetchData(), 100);
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col justify-between border-r border-slate-800">
        <div>
          {/* Logo */}
          <div className="p-6 border-b border-slate-800 flex items-center gap-3">
            <div className="h-9 w-9 bg-amber-500 rounded-lg flex items-center justify-center font-bold text-slate-900 text-lg">
              a
            </div>
            <div>
              <h1 className="font-bold text-sm leading-tight tracking-wider uppercase text-amber-500">Amazon</h1>
              <p className="text-xs text-slate-400 font-semibold">Auto Lister</p>
            </div>
          </div>
          
          {/* Navigation Links */}
          <nav className="p-4 flex flex-col gap-1.5">
            <button 
              onClick={() => setActiveTab("dashboard")}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "dashboard" ? "bg-amber-500 text-slate-900 font-semibold" : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <LayoutDashboard size={18} />
              Dashboard
            </button>
            <button 
              onClick={() => setActiveTab("upload")}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "upload" ? "bg-amber-500 text-slate-900 font-semibold" : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <UploadCloud size={18} />
              Upload Center
            </button>
            <button 
              onClick={() => setActiveTab("learning")}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "learning" ? "bg-amber-500 text-slate-900 font-semibold" : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <BrainCircuit size={18} />
              AI Learning Center
            </button>
            <button 
              onClick={() => {
                setActiveTab("generator");
              }}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "generator" ? "bg-amber-500 text-slate-900 font-semibold" : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <FileSpreadsheet size={18} />
              Listing Generator
            </button>
            <button 
              onClick={() => setActiveTab("settings")}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "settings" ? "bg-amber-500 text-slate-900 font-semibold" : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <Settings size={18} />
              Listing Settings
            </button>
            
            {taskDetail && (
              <button 
                onClick={() => setActiveTab("logs")}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all bg-slate-800 text-amber-500 border border-slate-700 animate-pulse`}
              >
                <Loader2 className="animate-spin" size={16} />
                Live Task running...
              </button>
            )}
          </nav>
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t border-slate-800 text-slate-500 text-xs text-center flex flex-col gap-1">
          <p className="font-medium text-slate-400">Enterprise SaaS Mode</p>
          <div className="flex items-center justify-center gap-1.5 text-[10px]">
            <span className="h-2 w-2 rounded-full bg-green-500 animate-ping"></span>
            <span>API Online</span>
          </div>
          <button 
            onClick={fetchData}
            className="mt-2 text-slate-400 hover:text-amber-500 flex items-center justify-center gap-1 mx-auto text-[10px] hover:underline"
          >
            <RefreshCw size={10} />
            Refresh Data
          </button>
        </div>
      </aside>

      {/* MAIN CONTAINER */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-bold text-lg text-slate-800 capitalize">{activeTab.replace("-", " ")}</h2>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-slate-500 text-xs flex items-center gap-1">
              <span>Server:</span>
              <button 
                onClick={handleUpdateApiUrl}
                className="font-semibold text-slate-700 hover:text-amber-600 hover:underline cursor-pointer transition-colors"
                title="Click to edit Backend API URL"
              >
                {currentApiUrl}
              </button>
            </div>
            <div className="h-8 w-px bg-slate-200"></div>
            <div className="flex items-center gap-2">
              <span className="text-slate-700 text-xs font-semibold">Administrator</span>
              <div className="h-8 w-8 rounded-full bg-slate-200 border border-slate-300 flex items-center justify-center text-xs font-bold text-slate-600">
                AD
              </div>
            </div>
          </div>
        </header>

        {/* Content View Area */}
        <div className="flex-1 overflow-y-auto p-8">
          
          {/* TAB 1: DASHBOARD */}
          {activeTab === "dashboard" && (
            <div className="flex flex-col gap-6">
              {/* Metrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Learned Mappings</span>
                  <div className="flex items-baseline justify-between mt-2">
                    <span className="text-3xl font-extrabold text-slate-800">{mappings.column_mappings.length}</span>
                    <span className="text-xs text-green-500 font-semibold">Active</span>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Learned Translations</span>
                  <div className="flex items-baseline justify-between mt-2">
                    <span className="text-3xl font-extrabold text-slate-800">{mappings.value_mappings.length}</span>
                    <span className="text-xs text-amber-500 font-semibold">Translating</span>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Hardcoded Defaults</span>
                  <div className="flex items-baseline justify-between mt-2">
                    <span className="text-3xl font-extrabold text-slate-800">{Object.keys(defaults).length}</span>
                    <span className="text-xs text-slate-400 font-semibold">Constant values</span>
                  </div>
                </div>
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Generated Tasks</span>
                  <div className="flex items-baseline justify-between mt-2">
                    <span className="text-3xl font-extrabold text-slate-800">{tasks.length}</span>
                    <span className="text-xs text-green-500 font-semibold">Success 100%</span>
                  </div>
                </div>
              </div>

              {/* Recent Generation runs */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                <div className="p-5 border-b border-slate-200 flex justify-between items-center">
                  <h3 className="font-bold text-slate-800 text-sm">Recent Listing Tasks</h3>
                  <button 
                    onClick={() => setActiveTab("generator")}
                    className="text-xs text-amber-600 hover:text-amber-700 font-semibold flex items-center gap-1.5"
                  >
                    <Plus size={14} /> New Listing Task
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                        <th className="p-4">Task ID</th>
                        <th className="p-4">Status</th>
                        <th className="p-4">Progress</th>
                        <th className="p-4">SKUs Count</th>
                        <th className="p-4">Created At</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {tasks.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="p-8 text-center text-slate-400">
                            No listings generated yet.
                          </td>
                        </tr>
                      ) : (
                        tasks.slice(0, 5).map((t: any) => (
                          <tr key={t.id} className="hover:bg-slate-50">
                            <td className="p-4 font-mono text-[10px] text-slate-600">{t.id}</td>
                            <td className="p-4">
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                t.status === "completed" ? "bg-green-100 text-green-700" :
                                t.status === "failed" ? "bg-red-100 text-red-700" : "bg-blue-100 text-blue-700"
                              }`}>
                                {t.status}
                              </span>
                            </td>
                            <td className="p-4">
                              <div className="w-24 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                                <div className="bg-amber-500 h-1.5" style={{ width: `${t.progress}%` }}></div>
                              </div>
                            </td>
                            <td className="p-4 font-medium">{t.skus_count}</td>
                            <td className="p-4 text-slate-500">{new Date(t.created_at).toLocaleString()}</td>
                            <td className="p-4 text-right">
                              <button 
                                onClick={async () => {
                                  setCurrentTaskId(t.id);
                                  const res = await fetch(`${API_URL}/api/tasks/${t.id}`);
                                  if (res.ok) setTaskDetail(await res.json());
                                  setActiveTab("logs");
                                }}
                                className="text-amber-600 hover:text-amber-700 font-semibold hover:underline"
                              >
                                View Logs
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: UPLOAD CENTER */}
          {activeTab === "upload" && (
            <div className="flex flex-col gap-6">
              {/* Info panel */}
              <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl text-xs text-amber-800 leading-relaxed">
                <strong>Upload instructions:</strong> Populate the 4 base data templates below. To feed the learning engine, upload complete, historically successful Amazon marketplace flat files in the **Historical Amazon Listings** section and click "Train Engine".
              </div>

              {/* Upload Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* 1. Item Directory / Master Sheet */}
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between md:col-span-2">
                  <div>
                    <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
                      <FileSpreadsheet className="text-amber-500" size={16} /> 1. Item Directory / Master Sheet (Excel)
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                      Primary source file containing SKUs, Barcodes, Colors, measurements, fabric types, weights, sizes, HSN codes, and MSRP details.
                    </p>
                  </div>
                  <div className="mt-4">
                    {files.item_directory.length > 0 ? (
                      <div className="flex items-center justify-between bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-xs">
                        <span className="font-semibold text-slate-700 truncate max-w-[200px]">{files.item_directory[0].filename}</span>
                        <button onClick={() => handleDeleteFile(files.item_directory[0].id)} className="text-red-500 hover:text-red-700">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ) : (
                      <label className="border-2 border-dashed border-slate-200 hover:border-amber-400 hover:bg-slate-50 cursor-pointer rounded-lg p-6 flex flex-col items-center justify-center transition-all">
                        <UploadCloud size={24} className="text-slate-400" />
                        <span className="text-xs text-slate-600 mt-2 font-medium">Select Excel File</span>
                        <input type="file" onChange={(e) => handleFileUpload(e, "item_directory")} className="hidden" accept=".xlsx,.xlsm" />
                      </label>
                    )}
                  </div>
                </div>

                {/* 2. Content Sheet */}
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
                      <FileSpreadsheet className="text-amber-500" size={16} /> 2. Content Sheet (Excel)
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                      Contains descriptions, keywords, bullet points, titles, and item-specific copywriting.
                    </p>
                  </div>
                  <div className="mt-4">
                    {files.content_sheet.length > 0 ? (
                      <div className="flex items-center justify-between bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-xs">
                        <span className="font-semibold text-slate-700 truncate max-w-[200px]">{files.content_sheet[0].filename}</span>
                        <button onClick={() => handleDeleteFile(files.content_sheet[0].id)} className="text-red-500 hover:text-red-700">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ) : (
                      <label className="border-2 border-dashed border-slate-200 hover:border-amber-400 hover:bg-slate-50 cursor-pointer rounded-lg p-6 flex flex-col items-center justify-center transition-all">
                        <UploadCloud size={24} className="text-slate-400" />
                        <span className="text-xs text-slate-600 mt-2 font-medium">Select Excel File</span>
                        <input type="file" onChange={(e) => handleFileUpload(e, "content_sheet")} className="hidden" accept=".xlsx,.xlsm" />
                      </label>
                    )}
                  </div>
                </div>

                {/* 3. Target Amazon Template */}
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
                      <FileSpreadsheet className="text-amber-500" size={16} /> 3. Amazon Template File (Excel)
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                      The blank category-specific Amazon flat file template (e.g. Apparel / Shirts) to populate.
                    </p>
                  </div>
                  <div className="mt-4">
                    {files.amazon_template.length > 0 ? (
                      <div className="flex items-center justify-between bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-xs">
                        <span className="font-semibold text-slate-700 truncate max-w-[200px]">{files.amazon_template[0].filename}</span>
                        <button onClick={() => handleDeleteFile(files.amazon_template[0].id)} className="text-red-500 hover:text-red-700">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ) : (
                      <label className="border-2 border-dashed border-slate-200 hover:border-amber-400 hover:bg-slate-50 cursor-pointer rounded-lg p-6 flex flex-col items-center justify-center transition-all">
                        <UploadCloud size={24} className="text-slate-400" />
                        <span className="text-xs text-slate-600 mt-2 font-medium">Select Excel File</span>
                        <input type="file" onChange={(e) => handleFileUpload(e, "amazon_template")} className="hidden" accept=".xlsx,.xlsm" />
                      </label>
                    )}
                  </div>
                </div>
              </div>

              {/* 5. Historical Mappings Upload section */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2 mb-2">
                  <BrainCircuit className="text-amber-500" size={16} /> 5. Historical Amazon Listings (AI Learning Engine)
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed max-w-2xl">
                  Upload completed, successful Amazon listing templates (e.g. Shirt Flat Files you have uploaded before). The learning engine will match these against the 3 source directories using SKU/EAN matching to learn mapping rules, translations, and constant defaults automatically.
                </p>

                <div className="mt-6 flex flex-col md:flex-row gap-6 items-start">
                  <div className="w-full md:w-1/2">
                    <label className="border-2 border-dashed border-slate-200 hover:border-amber-400 hover:bg-slate-50 cursor-pointer rounded-lg p-8 flex flex-col items-center justify-center transition-all">
                      <UploadCloud size={32} className="text-slate-400" />
                      <span className="text-xs text-slate-600 mt-2 font-semibold">Upload Historical Listing</span>
                      <p className="text-[10px] text-slate-400 mt-1">.xlsm or .xlsx format</p>
                      <input type="file" onChange={(e) => handleFileUpload(e, "historical_listing")} className="hidden" accept=".xlsx,.xlsm" />
                    </label>
                  </div>

                  <div className="w-full md:w-1/2 bg-slate-50 rounded-xl border border-slate-200 p-4">
                    <h4 className="font-bold text-xs text-slate-700 uppercase tracking-wide mb-3">Uploaded Listing Files</h4>
                    {files.historical_listing.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No historical listing files uploaded.</p>
                    ) : (
                      <div className="flex flex-col gap-2">
                        {files.historical_listing.map((f: any) => (
                          <div key={f.id} className="bg-white p-3 rounded-lg border border-slate-200 flex items-center justify-between text-xs shadow-2xs">
                            <div className="flex items-center gap-2">
                              <FileText size={16} className="text-slate-400" />
                              <span className="font-semibold text-slate-700 truncate max-w-[200px]">{f.filename}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <button 
                                onClick={() => handleTrainEngine(f.id)}
                                disabled={loading.train}
                                className="bg-amber-500 hover:bg-amber-600 disabled:bg-slate-300 text-slate-900 font-bold px-3 py-1 rounded text-[10px] uppercase transition-all"
                              >
                                {loading.train ? "Training..." : "Train AI"}
                              </button>
                              <button onClick={() => handleDeleteFile(f.id)} className="text-red-500 hover:text-red-700">
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: AI LEARNING CENTER */}
          {activeTab === "learning" && (
            <div className="flex flex-col gap-6">
              {/* Header and Manual Override Option */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <h3 className="font-bold text-sm text-slate-800">Learned Column Mapping Rules</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Below are the matches discovered between internal database fields and Amazon listing attributes.
                  </p>
                </div>
              </div>

              {/* Mappings Tables */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Column Mappings */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="p-4 border-b border-slate-200 bg-slate-50">
                    <h4 className="font-bold text-xs text-slate-700 uppercase tracking-wider">Column Header Mappings</h4>
                  </div>
                  <div className="overflow-y-auto max-h-[400px]">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-50 text-slate-500 border-b border-slate-200">
                          <th className="p-3 font-semibold">Amazon Attribute</th>
                          <th className="p-3 font-semibold">Source Column</th>
                          <th className="p-3 font-semibold">Confidence</th>
                          <th className="p-3 font-semibold text-center">Active</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {mappings.column_mappings.length === 0 ? (
                          <tr>
                            <td colSpan={4} className="p-8 text-center text-slate-400 italic">No column mappings learned yet. Train the AI in the Upload Center first!</td>
                          </tr>
                        ) : (
                          mappings.column_mappings.map((m: any) => (
                            <tr key={m.id} className="hover:bg-slate-50">
                              <td className="p-3 font-medium text-slate-700 break-all">{m.amazon_attribute}</td>
                              <td className="p-3 font-mono text-slate-500">{m.internal_column}</td>
                              <td className="p-3">
                                <span className={`px-1.5 py-0.5 rounded-md font-semibold ${
                                  m.confidence_score > 0.8 ? "bg-green-50 text-green-700 border border-green-200" :
                                  m.confidence_score > 0.5 ? "bg-amber-50 text-amber-700 border border-amber-200" : "bg-slate-100 text-slate-700"
                                }`}>
                                  {Math.round(m.confidence_score * 100)}%
                                </span>
                              </td>
                              <td className="p-3 text-center">
                                <button onClick={() => handleToggleColumn(m.id)} className="text-slate-600 hover:text-slate-900 mx-auto">
                                  {m.is_active ? <ToggleRight className="text-green-500" size={24} /> : <ToggleLeft className="text-slate-400" size={24} />}
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Value Mappings (Translations) */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="p-4 border-b border-slate-200 bg-slate-50">
                    <h4 className="font-bold text-xs text-slate-700 uppercase tracking-wider">Value Translations (Size/Color)</h4>
                  </div>
                  <div className="overflow-y-auto max-h-[400px]">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-50 text-slate-500 border-b border-slate-200">
                          <th className="p-3 font-semibold">Attribute</th>
                          <th className="p-3 font-semibold">Source Value</th>
                          <th className="p-3 font-semibold">Amazon value</th>
                          <th className="p-3 font-semibold">Confidence</th>
                          <th className="p-3 text-right">Delete</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {mappings.value_mappings.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="p-8 text-center text-slate-400 italic">No value mapping translations learned yet.</td>
                          </tr>
                        ) : (
                          mappings.value_mappings.map((v: any) => (
                            <tr key={v.id} className="hover:bg-slate-50">
                              <td className="p-3 text-slate-600 break-all">{v.amazon_attribute}</td>
                              <td className="p-3 font-semibold text-slate-800">{v.internal_value}</td>
                              <td className="p-3 text-slate-700 font-bold">{v.amazon_value}</td>
                              <td className="p-3">{Math.round(v.confidence_score * 100)}%</td>
                              <td className="p-3 text-right">
                                <button onClick={() => handleDeleteValueMapping(v.id)} className="text-red-500 hover:text-red-700">
                                  <Trash2 size={14} />
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: LISTING GENERATOR */}
          {activeTab === "generator" && (
            <div className="flex flex-col gap-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Generation Form inputs */}
                <div className="lg:col-span-2 flex flex-col gap-6">
                  {/* Select sheets panel */}
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4">
                    <h3 className="font-bold text-sm text-slate-800">1. Select Listing Templates</h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                      <div className="flex flex-col gap-1.5">
                        <label className="font-semibold text-slate-600">Item Directory / Master Sheet:</label>
                        <select 
                          value={selectedDir}
                          onChange={(e) => {
                            setSelectedDir(e.target.value);
                            setSelectedMaster(e.target.value);
                          }}
                          className="p-2 border border-slate-200 rounded-lg bg-white"
                        >
                          <option value="">-- Choose File --</option>
                          {files.item_directory.map((f: any) => <option key={f.id} value={f.id}>{f.filename}</option>)}
                        </select>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label className="font-semibold text-slate-600">Content Sheet:</label>
                        <select 
                          value={selectedContent}
                          onChange={(e) => setSelectedContent(e.target.value)}
                          className="p-2 border border-slate-200 rounded-lg bg-white"
                        >
                          <option value="">-- Choose File --</option>
                          {files.content_sheet.map((f: any) => <option key={f.id} value={f.id}>{f.filename}</option>)}
                        </select>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label className="font-semibold text-slate-600">Amazon Target Template:</label>
                        <select 
                          value={selectedTemplate}
                          onChange={(e) => setSelectedTemplate(e.target.value)}
                          className="p-2 border border-slate-200 rounded-lg bg-white"
                        >
                          <option value="">-- Choose Blank Template --</option>
                          {files.amazon_template.map((f: any) => <option key={f.id} value={f.id}>{f.filename}</option>)}
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* SKU Input Panel */}
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4">
                    <div>
                      <h3 className="font-bold text-sm text-slate-800">2. Enter Products (SKUs / Style Codes)</h3>
                      <p className="text-xs text-slate-400 mt-0.5">Supports single SKU, multiple values comma-separated, or bulk style codes copy-paste.</p>
                    </div>
                    
                    <textarea 
                      rows={5}
                      value={skusInput}
                      onChange={(e) => setSkusInput(e.target.value)}
                      placeholder="Enter SKU lookup codes (e.g. PGTOPS002848, PBSRHS003072, etc.)"
                      className="p-3 border border-slate-200 rounded-lg text-xs font-mono w-full"
                    />
                    
                    <button 
                      onClick={handleGenerateListings}
                      disabled={loading.generate || !selectedDir || !selectedContent || !selectedTemplate}
                      className="w-full bg-amber-500 hover:bg-amber-600 disabled:bg-slate-200 disabled:text-slate-400 text-slate-900 font-bold py-3 rounded-lg flex items-center justify-center gap-2 text-sm shadow-sm transition-all"
                    >
                      {loading.generate ? (
                        <>
                          <Loader2 className="animate-spin" size={16} /> Generating Listing...
                        </>
                      ) : (
                        <>
                          <Play size={16} fill="currentColor" /> Run Listing Engine
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Listing generator instructions sidebar */}
                <div className="bg-slate-900 text-slate-400 p-6 rounded-xl border border-slate-800 flex flex-col gap-4 text-xs">
                  <h4 className="font-bold text-amber-500 uppercase tracking-wide text-xs">How generation works</h4>
                  
                  <div className="flex flex-col gap-3 leading-relaxed">
                    <p>
                      <strong>1. Lookup & Matching:</strong> The engine queries the item directory for child SKUs matching your search terms.
                    </p>
                    <p>
                      <strong>2. Relational Join:</strong> Matched children pull additional attributes from the Master and Content sheets.
                    </p>
                    <p>
                      <strong>3. Parent-Child Automation:</strong> Style codes are grouped. Color/size variations automatically spawn **Parent Rows** (`[StyleCode]-$P`) and link **Child Rows** with the appropriate relationship attributes.
                    </p>
                    <p>
                      <strong>4. Field Unlocking:</strong> Enforces the Product Type selection first, then maps only unlocked fields defined in PTD configuration.
                    </p>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 5: TASK LOGS */}
          {activeTab === "logs" && (
            <div className="flex flex-col gap-6">
              {taskDetail ? (
                <div className="flex flex-col gap-6">
                  {/* Task Header */}
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                      <h3 className="font-bold text-sm text-slate-800 flex items-center gap-2">
                        Task Running Status: 
                        <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase font-bold ${
                          taskDetail.status === "completed" ? "bg-green-100 text-green-700" :
                          taskDetail.status === "failed" ? "bg-red-100 text-red-700" : "bg-blue-100 text-blue-700 animate-pulse"
                        }`}>
                          {taskDetail.status}
                        </span>
                      </h3>
                      <p className="text-[10px] font-mono text-slate-400 mt-1">ID: {taskDetail.id}</p>
                    </div>
                    
                    {taskDetail.has_download && (
                      <button 
                        onClick={() => handleDownload(taskDetail.id)}
                        className="bg-green-600 hover:bg-green-700 text-white font-bold px-4 py-2.5 rounded-lg flex items-center gap-2 text-xs shadow-sm transition-all cursor-pointer"
                      >
                        <Download size={14} /> Download Ready Listing
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Log Terminal console */}
                    <div className="lg:col-span-2 bg-slate-950 text-slate-200 p-6 rounded-xl border border-slate-900 flex flex-col gap-3 min-h-[400px] shadow-lg">
                      <div className="border-b border-slate-800 pb-2 flex justify-between text-slate-500 text-[10px] uppercase tracking-wider font-semibold">
                        <span>Real-Time Logs</span>
                        {taskDetail.status === "processing" && <span className="animate-pulse text-amber-500 font-bold">● Live</span>}
                        {taskDetail.status === "completed" && <span className="text-green-500 font-bold">✓ Done</span>}
                        {taskDetail.status === "failed" && <span className="text-red-500 font-bold">✗ Failed</span>}
                      </div>
                      
                      <div className="flex-1 overflow-y-auto flex flex-col gap-1 max-h-[450px] pr-1">
                        {!taskDetail.log_messages ? (
                          <div className="flex items-center gap-2 text-slate-500 text-xs mt-4">
                            <Loader2 size={14} className="animate-spin" />
                            <span>Waiting for logs...</span>
                          </div>
                        ) : (
                          taskDetail.log_messages.split("\n").map((line: string, idx: number) => {
                            const trimmed = line.trim();
                            
                            // Empty line = visual divider
                            if (!trimmed) return <div key={idx} className="h-2" />;
                            
                            // ✅ Style success header lines
                            if (trimmed.startsWith("✅")) {
                              return (
                                <div key={idx} className="flex items-start gap-2 bg-green-950/60 border border-green-900/40 rounded-lg px-3 py-2 mt-1">
                                  <span className="text-green-400 text-sm leading-none mt-0.5">✅</span>
                                  <span className="text-green-300 font-semibold text-xs">{trimmed.slice(2).trim()}</span>
                                </div>
                              );
                            }
                            
                            // • Property lines (title, description, bullets)
                            if (trimmed.startsWith("•") || trimmed.startsWith("   •")) {
                              const content = trimmed.replace(/^•\s*/, "").trim();
                              const isWarning = content.includes("(Not found");
                              return (
                                <div key={idx} className={`flex items-start gap-2 px-3 py-1.5 rounded ml-2 text-xs ${isWarning ? "text-amber-400" : "text-slate-300"}`}>
                                  <span className={`mt-0.5 ${isWarning ? "text-amber-500" : "text-sky-400"}`}>›</span>
                                  <span>{content}</span>
                                </div>
                              );
                            }
                            
                            // - Child variant lines
                            if (trimmed.startsWith("-") || trimmed.startsWith("     -")) {
                              const content = trimmed.replace(/^-\s*/, "").trim();
                              return (
                                <div key={idx} className="flex items-start gap-2 px-3 py-1 rounded ml-6 text-[11px] text-slate-400">
                                  <span className="text-slate-600 mt-0.5">⌙</span>
                                  <span>{content}</span>
                                </div>
                              );
                            }
                            
                            // ERROR lines
                            if (trimmed.startsWith("ERROR") || trimmed.startsWith("Traceback") || trimmed.startsWith("  File")) {
                              return (
                                <div key={idx} className="flex items-start gap-2 bg-red-950/60 border border-red-900/40 rounded px-3 py-1.5 text-xs text-red-300">
                                  <AlertCircle size={12} className="mt-0.5 flex-shrink-0 text-red-400" />
                                  <span className="font-mono break-all">{trimmed}</span>
                                </div>
                              );
                            }

                            // WARNING lines
                            if (trimmed.startsWith("WARNING") || trimmed.startsWith("⚠")) {
                              return (
                                <div key={idx} className="flex items-start gap-2 bg-amber-950/40 rounded px-3 py-1.5 text-xs text-amber-300">
                                  <span className="mt-0.5">⚠</span>
                                  <span>{trimmed.replace(/^(WARNING:|⚠)\s*/, "")}</span>
                                </div>
                              );
                            }
                            
                            // Default: plain info line
                            return (
                              <div key={idx} className="text-xs text-slate-400 px-2 py-0.5">
                                {trimmed}
                              </div>
                            );
                          })
                        )}
                        {taskDetail.status === "processing" && (
                          <div className="flex items-center gap-2 text-amber-400 text-xs mt-2 px-2">
                            <Loader2 size={12} className="animate-spin" />
                            <span>Processing...</span>
                          </div>
                        )}
                      </div>
                    </div>


                    {/* Validation Panel */}
                    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4 text-xs">
                      <h4 className="font-bold text-sm text-slate-800 border-b border-slate-100 pb-2">Pre-Export Validation Report</h4>
                      
                      {!taskDetail.validation || Object.keys(taskDetail.validation).length === 0 ? (
                        <p className="text-slate-400 italic">No validation report generated yet.</p>
                      ) : (
                        <div className="flex flex-col gap-4">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold">Compliance Status:</span>
                            <span className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                              taskDetail.validation.is_valid ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                            }`}>
                              {taskDetail.validation.is_valid ? "Compliant" : "Has Errors"}
                            </span>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-4 border-y border-slate-100 py-3">
                            <div className="text-center">
                              <span className="text-2xl font-bold text-red-600">{taskDetail.validation.errors_count}</span>
                              <p className="text-[10px] text-slate-500 font-medium">Errors</p>
                            </div>
                            <div className="text-center">
                              <span className="text-2xl font-bold text-amber-600">{taskDetail.validation.warnings_count}</span>
                              <p className="text-[10px] text-slate-500 font-medium">Warnings</p>
                            </div>
                          </div>

                          {/* Errors List */}
                          {taskDetail.validation.errors && taskDetail.validation.errors.length > 0 && (
                            <div className="flex flex-col gap-1.5">
                              <span className="font-bold text-red-600 text-[10px] uppercase">Critical Errors ({taskDetail.validation.errors.length})</span>
                              <div className="max-h-[150px] overflow-y-auto border border-red-100 bg-red-50/50 rounded-lg p-2 flex flex-col gap-1 text-[10px] text-red-700">
                                {taskDetail.validation.errors.map((e: any, idx: number) => (
                                  <div key={idx} className="flex gap-1.5 items-start">
                                    <AlertCircle size={10} className="mt-0.5 flex-shrink-0" />
                                    <span>{e}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Warnings List */}
                          {taskDetail.validation.warnings && taskDetail.validation.warnings.length > 0 && (
                            <div className="flex flex-col gap-1.5">
                              <span className="font-bold text-amber-600 text-[10px] uppercase">Warnings ({taskDetail.validation.warnings.length})</span>
                              <div className="max-h-[150px] overflow-y-auto border border-amber-100 bg-amber-50/50 rounded-lg p-2 flex flex-col gap-1 text-[10px] text-amber-700">
                                {taskDetail.validation.warnings.map((w: any, idx: number) => (
                                  <div key={idx} className="flex gap-1.5 items-start">
                                    <HelpCircle size={10} className="mt-0.5 flex-shrink-0" />
                                    <span>{w}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-400">
                  <FileText className="mx-auto text-slate-300 mb-2" size={32} />
                  No task selected. Run a listing job in the Listing Generator tab to view logs.
                </div>
              )}
            </div>
          )}

          {/* TAB 6: LISTING SETTINGS */}
          {activeTab === "settings" && (
            <div className="flex flex-col gap-6">
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                
                {/* 1. Hardcoded Constant Defaults */}
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4">
                  <div>
                    <h3 className="font-bold text-sm text-slate-800">Hardcoded Constant Defaults</h3>
                    <p className="text-xs text-slate-500 mt-1">
                      Configure columns that always contain the exact same constant value across every single listing generated.
                    </p>
                  </div>
                  
                  {/* Current defaults */}
                  <div className="border border-slate-200 rounded-lg overflow-hidden text-xs">
                    <div className="bg-slate-50 p-2.5 font-bold text-slate-600 border-b border-slate-200 flex">
                      <span className="w-1/2">Amazon Attribute</span>
                      <span className="w-1/2">Constant Default Value</span>
                    </div>
                    <div className="divide-y divide-slate-100 max-h-[200px] overflow-y-auto">
                      {Object.keys(defaults).length === 0 ? (
                        <p className="p-4 text-center text-slate-400 italic">No defaults set. Define one below!</p>
                      ) : (
                        Object.entries(defaults).map(([attr, val]: [string, any]) => (
                          <div key={attr} className="p-2.5 flex justify-between items-center hover:bg-slate-50">
                            <span className="w-1/2 font-mono text-[10px] text-slate-600 break-all pr-2">{attr}</span>
                            <span className="w-5/12 font-semibold text-slate-700 truncate">{val}</span>
                            <button onClick={() => handleDeleteDefault(attr)} className="text-red-500 hover:text-red-700">
                              <Trash2 size={12} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Add default form */}
                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex flex-col gap-3 text-xs">
                    <span className="font-bold text-slate-700 text-[10px] uppercase">Add New Default Value</span>
                    <div className="flex gap-2">
                      <input 
                        type="text"
                        value={newDefaultAttr}
                        onChange={(e) => setNewDefaultAttr(e.target.value)}
                        placeholder="Amazon Attribute (e.g. brandOwner)"
                        className="w-1/2 p-2 border border-slate-200 rounded-lg bg-white text-xs font-mono"
                      />
                      <input 
                        type="text"
                        value={newDefaultVal}
                        onChange={(e) => setNewDefaultVal(e.target.value)}
                        placeholder="Constant Value (e.g. India)"
                        className="w-5/12 p-2 border border-slate-200 rounded-lg bg-white text-xs"
                      />
                      <button onClick={handleAddDefault} className="bg-slate-900 hover:bg-slate-800 text-white font-bold p-2.5 rounded-lg flex-shrink-0">
                        <Plus size={14} />
                      </button>
                    </div>
                  </div>
                </div>

                {/* 2. Priority Override Rules */}
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-4">
                  <div>
                    <h3 className="font-bold text-sm text-slate-800">Priority Scope Override Rules</h3>
                    <p className="text-xs text-slate-500 mt-1">
                      Set target rules mapping priorities over other sources. Scope takes precedence: Product Type &gt; Brand &gt; Category &gt; Global.
                    </p>
                  </div>
                  
                  {/* Current rules */}
                  <div className="border border-slate-200 rounded-lg overflow-hidden text-xs">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-50 text-slate-600 border-b border-slate-200 font-bold">
                          <th className="p-2">Scope</th>
                          <th className="p-2">Scope Val</th>
                          <th className="p-2">Attribute</th>
                          <th className="p-2">Rule Value</th>
                          <th className="p-2 text-right">Delete</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 max-h-[200px] overflow-y-auto">
                        {rules.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="p-8 text-center text-slate-400 italic">No scope rules defined yet.</td>
                          </tr>
                        ) : (
                          rules.map((r: any) => (
                            <tr key={r.id} className="hover:bg-slate-50">
                              <td className="p-2 capitalize font-semibold text-amber-600">{r.scope}</td>
                              <td className="p-2 font-medium text-slate-700">{r.scope_value || "—"}</td>
                              <td className="p-2 font-mono text-[10px] break-all max-w-[100px]">{r.amazon_attribute}</td>
                              <td className="p-2 font-semibold truncate max-w-[100px]">{r.rule_value}</td>
                              <td className="p-2 text-right">
                                <button onClick={() => handleDeleteRule(r.id)} className="text-red-500 hover:text-red-700">
                                  <Trash2 size={12} />
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Add rule form */}
                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex flex-col gap-3 text-xs">
                    <span className="font-bold text-slate-700 text-[10px] uppercase">Create Scope Override Rule</span>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-slate-500 font-semibold">Scope:</label>
                        <select 
                          value={newRuleScope} 
                          onChange={(e) => setNewRuleScope(e.target.value)}
                          className="p-2 border border-slate-200 rounded-lg bg-white"
                        >
                          <option value="global">Global</option>
                          <option value="product_type">Product Type</option>
                          <option value="brand">Brand</option>
                          <option value="category">Category</option>
                        </select>
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-slate-500 font-semibold">Scope Value (e.g. Brand Name):</label>
                        <input 
                          type="text" 
                          value={newRuleScopeVal} 
                          onChange={(e) => setNewRuleScopeVal(e.target.value)}
                          disabled={newRuleScope === "global"}
                          placeholder="e.g. SHIRT or BrandOwner"
                          className="p-2 border border-slate-200 rounded-lg bg-white"
                        />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <input 
                        type="text" 
                        value={newRuleAttr} 
                        onChange={(e) => setNewRuleAttr(e.target.value)}
                        placeholder="Amazon Attribute"
                        className="w-1/2 p-2 border border-slate-200 rounded-lg bg-white font-mono"
                      />
                      <input 
                        type="text" 
                        value={newRuleVal} 
                        onChange={(e) => setNewRuleVal(e.target.value)}
                        placeholder="Rule Override Value"
                        className="w-5/12 p-2 border border-slate-200 rounded-lg bg-white"
                      />
                      <button onClick={handleAddRule} className="bg-slate-900 hover:bg-slate-800 text-white font-bold p-2.5 rounded-lg flex-shrink-0">
                        <Plus size={14} />
                      </button>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
