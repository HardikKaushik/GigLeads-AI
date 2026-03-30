"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const MODULES = [
  { key: "leads", label: "Leads", desc: "Find potential B2B clients and send personalized outreach", icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" },
  { key: "gigs", label: "Gigs", desc: "Discover freelance projects on Upwork, LinkedIn & more", icon: "M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m8 0H8m8 0h2a2 2 0 012 2v6a2 2 0 01-2 2H6a2 2 0 01-2-2V8a2 2 0 012-2h2" },
  { key: "jobs", label: "Jobs", desc: "Find full-time & contract positions with auto-apply", icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" },
];

export default function OnboardingPage() {
  const { refreshUser } = useAuth();
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [selected, setSelected] = useState<string[]>(["leads", "gigs", "jobs"]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Common fields
  const [skills, setSkills] = useState("");
  const [portfolio, setPortfolio] = useState("");

  // Leads fields
  const [targetIndustry, setTargetIndustry] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [decisionMakerRoles, setDecisionMakerRoles] = useState("");

  // Gigs fields
  const [gigPlatforms, setGigPlatforms] = useState<string[]>(["upwork", "linkedin"]);
  const [hourlyRate, setHourlyRate] = useState("");

  // Jobs fields
  const [desiredRole, setDesiredRole] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("mid");
  const [locationPref, setLocationPref] = useState("");
  const [salaryRange, setSalaryRange] = useState("");
  const [remotePreference, setRemotePreference] = useState(true);

  const toggleModule = (key: string) => {
    setSelected((prev) =>
      prev.includes(key) ? prev.filter((m) => m !== key) : [...prev, key]
    );
  };

  const togglePlatform = (p: string) => {
    setGigPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  };

  const handleComplete = async () => {
    setSaving(true);
    setError("");
    try {
      await api.updateModules(selected);

      const onboardingData: Record<string, unknown> = {
        common: {
          skills: skills.split(",").map((s) => s.trim()).filter(Boolean),
          portfolio,
        },
      };

      if (selected.includes("leads")) {
        onboardingData.leads = {
          target_industry: targetIndustry,
          company_size: companySize,
          decision_maker_roles: decisionMakerRoles,
        };
      }

      if (selected.includes("gigs")) {
        onboardingData.gigs = {
          platforms_preference: gigPlatforms,
          hourly_rate: hourlyRate ? parseFloat(hourlyRate) : null,
        };
      }

      if (selected.includes("jobs")) {
        onboardingData.jobs = {
          desired_role: desiredRole,
          experience_level: experienceLevel,
          location_preference: locationPref,
          salary_range: salaryRange,
          remote: remotePreference,
        };
      }

      await api.completeOnboarding(onboardingData);
      await refreshUser();
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 text-lg font-bold text-white">
            AI
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Set up your workspace</h1>
          <p className="mt-1 text-sm text-gray-500">Step {step} of 2</p>
        </div>

        {/* Progress bar */}
        <div className="mb-8 flex gap-2">
          {[1, 2].map((s) => (
            <div
              key={s}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                s <= step ? "bg-blue-600" : "bg-gray-200"
              }`}
            />
          ))}
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700">{error}</div>
        )}

        {/* Step 1: Module Selection */}
        {step === 1 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900">What do you want to use GigLeads AI for?</h2>
            <p className="mt-1 text-sm text-gray-500">Select one or more modules. You can change this later.</p>

            <div className="mt-6 space-y-3">
              {MODULES.map((m) => (
                <button
                  key={m.key}
                  onClick={() => toggleModule(m.key)}
                  className={`flex w-full items-center gap-4 rounded-xl border-2 p-4 text-left transition-all ${
                    selected.includes(m.key)
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 bg-white hover:border-gray-300"
                  }`}
                >
                  <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                    selected.includes(m.key) ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-500"
                  }`}>
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d={m.icon} />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900">{m.label}</p>
                    <p className="text-sm text-gray-500">{m.desc}</p>
                  </div>
                  <div className={`flex h-6 w-6 items-center justify-center rounded-full border-2 ${
                    selected.includes(m.key) ? "border-blue-600 bg-blue-600" : "border-gray-300"
                  }`}>
                    {selected.includes(m.key) && (
                      <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </button>
              ))}
            </div>

            <button
              onClick={() => setStep(2)}
              disabled={selected.length === 0}
              className="mt-6 w-full rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              Continue
            </button>
          </div>
        )}

        {/* Step 2: Details Form */}
        {step === 2 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Tell us about yourself</h2>
            <p className="mt-1 text-sm text-gray-500">This helps our AI find the best opportunities for you.</p>

            <div className="mt-6 space-y-6 rounded-xl border border-gray-200 bg-white p-6">
              {/* Common Fields */}
              <div>
                <h3 className="text-sm font-semibold uppercase text-gray-400">Your Profile</h3>
                <div className="mt-3 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Skills (comma-separated)</label>
                    <input value={skills} onChange={(e) => setSkills(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder="Python, React, FastAPI, Machine Learning" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Portfolio Summary</label>
                    <textarea value={portfolio} onChange={(e) => setPortfolio(e.target.value)} rows={3}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder="Describe your experience, past projects, key achievements..." />
                  </div>
                </div>
              </div>

              {/* Leads Fields */}
              {selected.includes("leads") && (
                <div>
                  <h3 className="text-sm font-semibold uppercase text-blue-600">Leads Settings</h3>
                  <div className="mt-3 grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Target Industry</label>
                      <input value={targetIndustry} onChange={(e) => setTargetIndustry(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                        placeholder="SaaS, FinTech, HealthTech" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Company Size</label>
                      <select value={companySize} onChange={(e) => setCompanySize(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                        <option value="">Any</option>
                        <option value="startup">Startup (1-50)</option>
                        <option value="smb">SMB (51-500)</option>
                        <option value="enterprise">Enterprise (500+)</option>
                      </select>
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-gray-700">Decision Maker Roles</label>
                      <input value={decisionMakerRoles} onChange={(e) => setDecisionMakerRoles(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                        placeholder="CTO, VP Engineering, Head of Product" />
                    </div>
                  </div>
                </div>
              )}

              {/* Gigs Fields */}
              {selected.includes("gigs") && (
                <div>
                  <h3 className="text-sm font-semibold uppercase text-purple-600">Gigs Settings</h3>
                  <div className="mt-3 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Preferred Platforms</label>
                      <div className="mt-2 flex gap-2">
                        {["upwork", "linkedin", "freelancer"].map((p) => (
                          <button key={p} onClick={() => togglePlatform(p)}
                            className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
                              gigPlatforms.includes(p)
                                ? "bg-purple-100 text-purple-700"
                                : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                            }`}>
                            {p}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="w-1/2">
                      <label className="block text-sm font-medium text-gray-700">Hourly Rate ($)</label>
                      <input value={hourlyRate} onChange={(e) => setHourlyRate(e.target.value)} type="number"
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                        placeholder="75" />
                    </div>
                  </div>
                </div>
              )}

              {/* Jobs Fields */}
              {selected.includes("jobs") && (
                <div>
                  <h3 className="text-sm font-semibold uppercase text-green-600">Jobs Settings</h3>
                  <div className="mt-3 grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Desired Role</label>
                      <input value={desiredRole} onChange={(e) => setDesiredRole(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                        placeholder="Senior Software Engineer" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Experience Level</label>
                      <select value={experienceLevel} onChange={(e) => setExperienceLevel(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                        <option value="junior">Junior (0-2 years)</option>
                        <option value="mid">Mid-level (2-5 years)</option>
                        <option value="senior">Senior (5-10 years)</option>
                        <option value="staff">Staff+ (10+ years)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Location Preference</label>
                      <input value={locationPref} onChange={(e) => setLocationPref(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                        placeholder="Remote, New York, SF" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Salary Range</label>
                      <input value={salaryRange} onChange={(e) => setSalaryRange(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                        placeholder="$120k - $180k" />
                    </div>
                    <div className="col-span-2">
                      <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                        <input type="checkbox" checked={remotePreference}
                          onChange={(e) => setRemotePreference(e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                        Open to remote positions
                      </label>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 flex gap-3">
              <button onClick={() => setStep(1)}
                className="flex-1 rounded-lg border border-gray-300 bg-white py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                Back
              </button>
              <button onClick={handleComplete} disabled={saving || !skills.trim()}
                className="flex-1 rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
                {saving ? "Setting up..." : "Get Started"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
