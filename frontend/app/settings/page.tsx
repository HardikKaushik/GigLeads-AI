"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const INDUSTRY_OPTIONS = [
  "All Industries",
  "SaaS",
  "FinTech",
  "HealthTech",
  "EdTech",
  "E-commerce",
  "AI / Machine Learning",
  "Cybersecurity",
  "Cloud Infrastructure",
  "Media & Entertainment",
  "Supply Chain / Logistics",
  "Real Estate Tech",
  "CleanTech / Energy",
  "Gaming",
  "Blockchain / Web3",
  "Consulting",
  "Government / Public Sector",
];

const COUNTRY_OPTIONS = [
  { value: "Remote", label: "Remote (Worldwide)" },
  { value: "United States", label: "United States" },
  { value: "India", label: "India" },
  { value: "United Kingdom", label: "United Kingdom" },
  { value: "Canada", label: "Canada" },
  { value: "Germany", label: "Germany" },
  { value: "Australia", label: "Australia" },
  { value: "Singapore", label: "Singapore" },
  { value: "UAE", label: "UAE" },
  { value: "Netherlands", label: "Netherlands" },
  { value: "France", label: "France" },
];

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");

  const [name, setName] = useState("");
  const [skills, setSkills] = useState("");
  const [portfolio, setPortfolio] = useState("");
  const [incomeGoal, setIncomeGoal] = useState("");
  const [targetIndustry, setTargetIndustry] = useState("All Industries");
  const [customIndustry, setCustomIndustry] = useState("");
  const [locationPref, setLocationPref] = useState("Remote");
  const [customCountry, setCustomCountry] = useState("");
  const [selectedModules, setSelectedModules] = useState<string[]>([]);

  useEffect(() => {
    if (!user) return;
    setName(user.name);
    setSkills(user.skills.join(", "));
    setPortfolio(user.portfolio || "");
    setIncomeGoal(user.income_goal ? String(user.income_goal) : "");
    setSelectedModules(user.selected_modules || []);

    // Parse target_industry
    const industry = user.target_industry || "";
    if (INDUSTRY_OPTIONS.includes(industry) || industry === "") {
      setTargetIndustry(industry || "All Industries");
      setCustomIndustry("");
    } else {
      setTargetIndustry("custom");
      setCustomIndustry(industry);
    }

    // Parse location from onboarding_data
    const onboarding = user.onboarding_data as Record<string, Record<string, string>> | null;
    const savedLocation = onboarding?.jobs?.location_preference || "Remote";
    const isKnownCountry = COUNTRY_OPTIONS.some((c) => c.value === savedLocation);
    if (isKnownCountry) {
      setLocationPref(savedLocation);
      setCustomCountry("");
    } else if (savedLocation) {
      setLocationPref("custom");
      setCustomCountry(savedLocation);
    }
  }, [user]);

  const getIndustryValue = () => {
    if (targetIndustry === "custom") return customIndustry;
    if (targetIndustry === "All Industries") return "";
    return targetIndustry;
  };

  const getLocationValue = () => {
    if (locationPref === "custom") return customCountry;
    return locationPref;
  };

  const saveProfile = async () => {
    setSaving(true);
    setSuccess("");
    try {
      await api.updateProfile({
        name,
        skills: skills.split(",").map((s) => s.trim()).filter(Boolean),
        portfolio: portfolio || null,
        income_goal: incomeGoal ? parseFloat(incomeGoal) : null,
        target_industry: getIndustryValue() || null,
      });

      // Also update onboarding_data with location preference
      const currentOnboarding = (user?.onboarding_data || {}) as Record<string, unknown>;
      const jobsData = (currentOnboarding.jobs || {}) as Record<string, string>;
      await api.completeOnboarding({
        ...currentOnboarding,
        jobs: {
          ...jobsData,
          location_preference: getLocationValue(),
        },
      });

      await refreshUser();
      setSuccess("Settings saved!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed to save");
    } finally { setSaving(false); }
  };

  const saveModules = async () => {
    if (selectedModules.length === 0) { alert("Select at least one module"); return; }
    try {
      await api.updateModules(selectedModules);
      await refreshUser();
      setSuccess("Modules updated!");
      setTimeout(() => setSuccess(""), 3000);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed to save");
    }
  };

  const toggleModule = (mod: string) => {
    setSelectedModules((prev) =>
      prev.includes(mod) ? prev.filter((m) => m !== mod) : [...prev, mod]
    );
  };

  if (!user) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
      <p className="mt-1 text-sm text-gray-500">Configure your freelance profile and search preferences</p>

      {success && (
        <div className="mt-4 rounded-lg bg-green-50 px-4 py-2.5 text-sm font-medium text-green-700">{success}</div>
      )}

      {/* Module Selection */}
      <div className="mt-6 max-w-2xl rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="font-semibold text-gray-900">Active Modules</h2>
        <p className="mt-1 text-sm text-gray-500">Choose which features to enable</p>
        <div className="mt-4 flex gap-3">
          {[
            { key: "leads", label: "Leads", color: "blue" },
            { key: "gigs", label: "Gigs", color: "purple" },
            { key: "jobs", label: "Jobs", color: "green" },
          ].map(({ key, label, color }) => (
            <button key={key} onClick={() => toggleModule(key)}
              className={`flex items-center gap-2 rounded-lg border-2 px-4 py-2.5 text-sm font-medium transition-all ${
                selectedModules.includes(key)
                  ? `border-${color}-500 bg-${color}-50 text-${color}-700`
                  : "border-gray-200 bg-white text-gray-500 hover:border-gray-300"
              }`}>
              <div className={`h-4 w-4 rounded-full border-2 ${
                selectedModules.includes(key)
                  ? `border-${color}-600 bg-${color}-600`
                  : "border-gray-300"
              }`}>
                {selectedModules.includes(key) && (
                  <svg className="h-full w-full text-white" viewBox="0 0 24 24" fill="none" strokeWidth={4} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              {label}
            </button>
          ))}
        </div>
        <button onClick={saveModules}
          className="mt-4 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 transition-colors">
          Save Modules
        </button>
      </div>

      {/* Profile */}
      <div className="mt-6 max-w-2xl rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="font-semibold text-gray-900">Profile</h2>
        <div className="mt-4 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Skills (comma-separated)</label>
            <input value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="Python, React, FastAPI, PostgreSQL"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Monthly Income Goal ($)</label>
            <input value={incomeGoal} onChange={(e) => setIncomeGoal(e.target.value)} type="number" placeholder="5000"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Portfolio Summary</label>
            <textarea value={portfolio} onChange={(e) => setPortfolio(e.target.value)} rows={4} placeholder="Describe your experience, projects, and expertise..."
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
        </div>
      </div>

      {/* Search Preferences */}
      <div className="mt-6 max-w-2xl rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="font-semibold text-gray-900">Search Preferences</h2>
        <p className="mt-1 text-sm text-gray-500">Control how the pipeline searches for jobs, gigs, and leads</p>
        <div className="mt-4 space-y-5">

          {/* Location Preference */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Location Preference</label>
            <p className="text-xs text-gray-400 mt-0.5">Choose Remote for worldwide or select a specific country</p>
            <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
              {COUNTRY_OPTIONS.map((opt) => (
                <button key={opt.value} onClick={() => { setLocationPref(opt.value); setCustomCountry(""); }}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
                    locationPref === opt.value
                      ? "border-blue-500 bg-blue-50 text-blue-700 ring-1 ring-blue-200"
                      : "border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50"
                  }`}>
                  {opt.value === "Remote" && "🌍 "}{opt.label}
                </button>
              ))}
              <button onClick={() => setLocationPref("custom")}
                className={`rounded-lg border px-3 py-2 text-xs font-medium transition-all ${
                  locationPref === "custom"
                    ? "border-blue-500 bg-blue-50 text-blue-700 ring-1 ring-blue-200"
                    : "border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50"
                }`}>
                Other...
              </button>
            </div>
            {locationPref === "custom" && (
              <input value={customCountry} onChange={(e) => setCustomCountry(e.target.value)}
                placeholder="Enter country or city" autoFocus
                className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            )}
          </div>

          {/* Target Industry */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Target Industry</label>
            <p className="text-xs text-gray-400 mt-0.5">Select &quot;All Industries&quot; for broadest results, or pick a specific industry</p>
            <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
              {INDUSTRY_OPTIONS.map((ind) => (
                <button key={ind} onClick={() => { setTargetIndustry(ind); setCustomIndustry(""); }}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition-all text-left ${
                    targetIndustry === ind
                      ? "border-green-500 bg-green-50 text-green-700 ring-1 ring-green-200"
                      : "border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50"
                  }`}>
                  {ind === "All Industries" && "🌐 "}{ind}
                </button>
              ))}
              <button onClick={() => setTargetIndustry("custom")}
                className={`rounded-lg border px-3 py-2 text-xs font-medium transition-all text-left ${
                  targetIndustry === "custom"
                    ? "border-green-500 bg-green-50 text-green-700 ring-1 ring-green-200"
                    : "border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50"
                }`}>
                Custom...
              </button>
            </div>
            {targetIndustry === "custom" && (
              <input value={customIndustry} onChange={(e) => setCustomIndustry(e.target.value)}
                placeholder="Enter your target industry" autoFocus
                className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            )}
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="mt-6 max-w-2xl">
        <button onClick={saveProfile} disabled={saving || !name}
          className="rounded-lg bg-blue-600 px-8 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm">
          {saving ? "Saving..." : "Save All Settings"}
        </button>
      </div>

      <div className="mt-4 mb-8 text-xs text-gray-400">
        Email: <code className="rounded bg-gray-100 px-1.5 py-0.5">{user.email}</code>
      </div>
    </div>
  );
}
