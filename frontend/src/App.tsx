/**
 * CV Generator — main application.
 *
 * One screen, two columns on desktop: the editor form on the left, a live
 * A4 preview on the right. State lives here so data is preserved while
 * users move between sections. A debounced draft autosave protects users
 * from losing their work to a refresh or closed tab.
 *
 * Two STRUCTURE choices drive the app:
 * - profile  -> section order + requirements (Experienced vs Fresher)
 * - template -> presentation (Classic / Compact / Modern)
 */
import { useEffect, useMemo, useRef, useState } from "react";
import StatusBanner, { type StatusKind } from "./components/StatusBanner";
import CVPreview, { ATSChecks } from "./components/CVPreview";
import EducationForm from "./components/EducationForm";
import ExperienceForm from "./components/ExperienceForm";
import ExtrasForm from "./components/ExtrasForm";
import ImportCV from "./components/ImportCV";
import PersonalForm from "./components/PersonalForm";
import ProfilePicker from "./components/ProfilePicker";
import ProjectsForm from "./components/ProjectsForm";
import SectionNavDefault, {
  NextSection,
  SECTION_IDS,
  scrollToSection,
} from "./components/SectionNav";
import SkillsForm from "./components/SkillsForm";
import SummaryForm from "./components/SummaryForm";
import TemplatePicker from "./components/TemplatePicker";
import ScoreCard from "./components/ScoreCard";
import ScoreChecker from "./components/ScoreChecker";
import { Btn, SectionCard } from "./components/ui";
import { getProfile, type ProfileKey } from "./data/profiles";
import Legal, { useHashRoute } from "./pages/Legal";
import {
  ApiError,
  checkBackendHealth,
  checkScore,
  generateCV,
  type ScoreResult,
} from "./services/api";
import {
  emptyCV,
  emptyCertification,
  emptyEducation,
  emptyExperience,
  emptyProject,
  type CVData,
} from "./types/cv";
import { downloadBlob } from "./utils/download";
import { sampleCV } from "./utils/sampleData";
import {
  clearDraft,
  draftAgeMinutes,
  hasContent,
  loadDraft,
  saveDraft,
} from "./utils/storage";
import {
  cvWarnings,
  isCVValid,
  validateCV,
  type CVProblems,
  type CVWarnings,
} from "./utils/validate";

export default function App() {
  // Tiny hash router: "" (builder), "/privacy" or "/terms".
  const [route, setRoute] = useState("");
  useHashRoute(setRoute);

  const [cv, setCv] = useState<CVData>(emptyCV);
  const [submitted, setSubmitted] = useState(false);
  const [status, setStatus] = useState<StatusKind>("idle");
  const [message, setMessage] = useState("");
  const [downloadName, setDownloadName] = useState("");

  // Draft restore: timestamp of an offered draft, null when none/no offer.
  const [draftInfo, setDraftInfo] = useState<number | null>(null);
  // "Draft saved ✓" flash visibility.
  const [savedFlash, setSavedFlash] = useState(false);
  // Backend health for the header indicator: null = checking.
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);
  // Mobile Editor/Preview tabs (relevant only under the tab breakpoint).
  const [mobileTab, setMobileTab] = useState<"editor" | "preview">("editor");
  // Import stays collapsed until requested — typing should always be the
  // fastest path into the product; upload is for a minority of users.
  const [importOpen, setImportOpen] = useState(false);

  /** Copy a shareable link to the app, with a 2s "Link copied!" flash. */
  async function copyShareLink() {
    const url = `${window.location.origin}${window.location.pathname}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Fallback for browsers/contexts without the async clipboard API.
      const ta = document.createElement("textarea");
      ta.value = url;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
      } catch {
        /* nothing more we can do */
      }
      ta.remove();
    }
    setShareCopied(true);
    window.clearTimeout(shareFlashTimer.current);
    shareFlashTimer.current = window.setTimeout(() => setShareCopied(false), 2000);
  }

  useEffect(() => () => window.clearTimeout(shareFlashTimer.current), []);
  // True while the on-screen keyboard is visible (Android resizes the
  // visual viewport) — used to hide the fixed bottom bars that would
  // otherwise ride up and cover the focused input.
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  // Post-download ATS score: offered after every successful generate, so a
  // brand-new CV can be scored the same way an imported one can. The score
  // describes the downloaded file — any later edit drops it.
  const [genScore, setGenScore] = useState<ScoreResult | null>(null);
  const [genScorePhase, setGenScorePhase] = useState<
    null | "offer" | "checking" | "shown" | "failed"
  >(null);
  // The exact file that was downloaded — re-scoring must not hit
  // /generate-cv a second time (server load + counter inflation).
  const lastDownloadRef = useRef<{ blob: Blob; filename: string } | null>(null);
  useEffect(() => {
    setGenScore(null);
    setGenScorePhase(null);
  }, [cv]);
  // "Link copied!" flash in the success block (2s).
  const [shareCopied, setShareCopied] = useState(false);
  const autosaveTimer = useRef<number | undefined>(undefined);
  const flashTimer = useRef<number | undefined>(undefined);
  const shareFlashTimer = useRef<number | undefined>(undefined);

  const problems: CVProblems = useMemo(() => validateCV(cv), [cv]);
  const warnings: CVWarnings = useMemo(() => cvWarnings(cv), [cv]);
  const profile = getProfile(cv.profile);

  function update(patch: Partial<CVData>) {
    setCv((prev) => ({ ...prev, ...patch }));
  }

  function setProfile(key: ProfileKey) {
    setCv((prev) => ({ ...prev, profile: key }));
  }

  function addItem<K extends "experience" | "education" | "projects" | "certifications">(
    field: K,
    item: CVData[K][number],
  ) {
    setCv((prev) => ({ ...prev, [field]: [...prev[field], item] }));
  }

  // ---- Draft autosave & restore ----

  // Offer a saved draft once on mount (never restore silently).
  useEffect(() => {
    const draft = loadDraft();
    if (draft) setDraftInfo(Date.now());
  }, []);

  // Debounced save: ~500ms after the last change, only when there is
  // content (so mount-time empty state can't wipe a stored draft).
  useEffect(() => {
    window.clearTimeout(autosaveTimer.current);
    autosaveTimer.current = window.setTimeout(() => {
      if (hasContent(cv)) {
        saveDraft(cv);
        setSavedFlash(true);
        window.clearTimeout(flashTimer.current);
        flashTimer.current = window.setTimeout(() => setSavedFlash(false), 2000);
      }
    }, 500);
    return () => {
      window.clearTimeout(autosaveTimer.current);
      window.clearTimeout(flashTimer.current);
    };
  }, [cv]);

  function restoreDraft() {
    const draft = loadDraft();
    if (draft) {
      setCv(draft);
      setSubmitted(false);
      setStatus("idle");
      setMessage("");
    }
    setDraftInfo(null);
  }

  function discardDraft() {
    clearDraft();
    setDraftInfo(null);
  }

  // ---- Data actions ----

  /** Apply imported CV data, keeping the user's current template/profile. */
  function applyImported(imported: Partial<CVData>) {
    setCv((prev) => ({
      ...emptyCV(),
      ...imported,
      profile: prev.profile,
      template: prev.template,
      contact: { ...emptyCV().contact, ...(imported.contact ?? {}) },
    } as CVData));
    setSubmitted(false);
    setStatus("success");
    setMessage(
      "Brought it in — give each section a quick once-over, then download.",
    );
    scrollToSection(SECTION_IDS.personal);
  }

  function loadSample() {
    setCv(sampleCV(cv.profile === "fresher" ? "fresher" : "experienced"));
    setSubmitted(false);
    setStatus("idle");
    setMessage("");
  }

  // Header/footer "ATS score" links. On mobile the editor pane is hidden
  // unless its tab is active, so switch tabs before scrolling to the card.
  function goToScoreChecker() {
    setMobileTab("editor");
    requestAnimationFrame(() => scrollToSection("score-checker"));
  }

  function resetForm() {
    setCv(emptyCV());
    clearDraft();
    setSubmitted(false);
    setStatus("idle");
    setMessage("");
    setDownloadName("");
    setGenScore(null);
    setGenScorePhase(null);
    lastDownloadRef.current = null;
    // Allow the next editing session to re-warm the backend (it may have
    // gone back to sleep by then).
    warmedUpRef.current = false;
  }

  async function handleGenerate(format: "docx" | "pdf") {
    // Re-entrancy guard: the buttons are also gated on `loading`, but this
    // catches fast double-taps racing React's re-render — parallel POSTs
    // mean duplicate files and multiplied load on a free-tier backend that
    // may be mid-cold-start.
    if (status === "loading") return;

    setSubmitted(true);
    if (!isCVValid(problems)) {
      setStatus("error");
      setMessage("A few things need filling in first — they're highlighted above.");
      return;
    }

    setStatus("loading");
    setMessage(format === "pdf" ? "Building your PDF…" : "Building your Word file…");
    // After 8s of silence (a cold start can run 30–50s), set expectations
    // so the wait reads as "working" instead of "broken". Cleared as soon
    // as the request settles so it never overwrites the real result.
    const expectTimer = window.setTimeout(() => {
      setMessage(
        "Still going… the server dozed off. Give it another 20 seconds.",
      );
    }, 8_000);
    try {
      const { blob, filename } = await generateCV(cv, format);
      window.clearTimeout(expectTimer);
      downloadBlob(blob, filename);
      setDownloadName(filename);
      lastDownloadRef.current = { blob, filename };
      setStatus("success");
      setMessage(`Got it — ${filename} is in your downloads folder.`);
      setGenScore(null);
      setGenScorePhase("offer");
    } catch (err) {
      window.clearTimeout(expectTimer);
      setStatus("error");
      setMessage(
        err instanceof ApiError
          ? err.message
          : "That didn't work — try again? If it keeps failing, the server might be waking up.",
      );
    }
  }

  /**
   * Score the file that was just downloaded, using the exact blob the user
   * received (no second generation). Any failure is soft — the score is a
   * bonus, never a blocker.
   */
  async function scoreGenerated() {
    const last = lastDownloadRef.current;
    if (!last) {
      setGenScorePhase("failed");
      return;
    }
    setGenScorePhase("checking");
    try {
      const result = await checkScore(last.blob, { filename: last.filename });
      setGenScore(result);
      setGenScorePhase("shown");
    } catch {
      setGenScorePhase("failed");
    }
  }

  // Real backend health for the header indicator.
  useEffect(() => {
    let cancelled = false;
    checkBackendHealth().then((ok) => {
      if (!cancelled) setApiHealthy(ok);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Pre-warm + keep-alive: Render's free tier sleeps after ~15 idle minutes.
  // The mount-time health check wakes the API once, but a user who types for
  // longer would still hit a 30–50s cold start at the moment they click
  // Download. So: the first edit fires a warm-up ping, and while there is
  // content a light keep-alive keeps the instance awake. Cheap for us (one
  // JSON GET), invisible for the user — and every ping doubles as a health
  // update for the header indicator.
  const warmedUpRef = useRef(false);
  const keepAliveIdRef = useRef<number | null>(null);
  useEffect(() => {
    // No content -> no reason to burn host hours; stop any keep-alive.
    if (!hasContent(cv)) {
      if (keepAliveIdRef.current !== null) {
        window.clearInterval(keepAliveIdRef.current);
        keepAliveIdRef.current = null;
      }
      return;
    }
    if (!warmedUpRef.current) {
      warmedUpRef.current = true;
      checkBackendHealth().then((ok) => {
        setApiHealthy(ok);
      });
    }
    // (Re)start a single keep-alive while content exists; the cleanup
    // below plus the empty-content branch above guarantee it never runs
    // forever once the editor is cleared or unmounted.
    if (keepAliveIdRef.current === null) {
      keepAliveIdRef.current = window.setInterval(() => {
        if (document.visibilityState !== "visible") return;
        void checkBackendHealth().then((ok) => {
          setApiHealthy(ok);
        });
      }, 10 * 60_000);
    }
    return () => {
      // Always stop on cleanup (unmount / re-run); the effect body above
      // restarts the single interval only while content exists.
      if (keepAliveIdRef.current !== null) {
        window.clearInterval(keepAliveIdRef.current);
        keepAliveIdRef.current = null;
      }
    };
  }, [cv]);

  // Keyboard-aware fixed bars: Chrome Android resizes the visual viewport
  // when the keyboard opens and position:fixed elements re-anchor to it —
  // riding up over the focused input. Hide both bars while typing (iOS
  // covers them with the keyboard anyway, so behavior evens out).
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const onResize = () => setKeyboardOpen(vv.height < window.innerHeight * 0.75);
    onResize();
    vv.addEventListener("resize", onResize);
    return () => vv.removeEventListener("resize", onResize);
  }, []);

  /** Editor card for a middle section, in profile order. */
  const middleCards = profile.middleSections.map((section) => {
    switch (section) {
      case "experience":
        return (
          <SectionCard
            key="experience"
            id={SECTION_IDS.experience}
            title={profile.key === "fresher" ? "Internships / Part-time work" : "Work experience"}
            subtitle={
              profile.key === "fresher"
                ? "Optional for freshers — internships and part-time roles fit here."
                : "Newest first. Achievement bullets make each job stronger."
            }
            actions={
              <Btn
                variant="soft"
                onClick={() => addItem("experience", emptyExperience())}
              >
                {profile.key === "fresher" ? "+ Add internship" : "+ Add job"}
              </Btn>
            }
          >
            <ExperienceForm cv={cv} warnings={warnings} update={update} />
            <NextSection
              targetId={nextIdAfter("experience", profile.middleSections)}
              label={labelAfter("experience", profile.middleSections)}
            />
          </SectionCard>
        );
      case "projects":
        return (
          <SectionCard
            key="projects"
            id={SECTION_IDS.projects}
            title="Projects"
            subtitle={
              profile.key === "fresher"
                ? "The heart of an entry-level CV — add your best 1–3."
                : "Showcase your best work."
            }
            actions={
              <Btn variant="soft" onClick={() => addItem("projects", emptyProject())}>
                + Add project
              </Btn>
            }
          >
            <ProjectsForm cv={cv} update={update} />
            <NextSection
              targetId={nextIdAfter("projects", profile.middleSections)}
              label={labelAfter("projects", profile.middleSections)}
            />
          </SectionCard>
        );
      case "education":
        return (
          <SectionCard
            key="education"
            id={SECTION_IDS.education}
            title="Education"
            subtitle={profile.key === "fresher" ? "Your degree — this leads the CV." : "Degree + school."}
            actions={
              <Btn variant="soft" onClick={() => addItem("education", emptyEducation())}>
                + Add education
              </Btn>
            }
          >
            <EducationForm cv={cv} update={update} />
            <NextSection
              targetId={nextIdAfter("education", profile.middleSections)}
              label={labelAfter("education", profile.middleSections)}
            />
          </SectionCard>
        );
      default:
        return null;
    }
  });

  /** The "extras" card always follows the middle sections. */

  function nextIdAfter(section: string, order: readonly string[]): string {
    const idx = order.indexOf(section);
    const next = order[idx + 1];
    if (next) return SECTION_IDS[next as keyof typeof SECTION_IDS];
    return SECTION_IDS.extras;
  }

  function labelAfter(section: string, order: readonly string[]): string {
    const idx = order.indexOf(section);
    const next = order[idx + 1];
    if (!next) return "Extras";
    const labels: Record<string, string> = {
      experience: profile.key === "fresher" ? "Internships" : "Experience",
      projects: "Projects",
      education: "Education",
    };
    return labels[next] ?? "Extras";
  }

  if (route === "/privacy" || route === "/terms") {
    return <Legal route={route} />;
  }

  return (
    <>
      <a className="skip-link" href="#editor">Skip to the CV editor</a>
      <header className="nav">
        <div className="nav-inner">
          <a className="logo" href="#editor">
            <span className="logo-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z" />
              </svg>
            </span>
            <span className="logo-text">ATS CV Generator</span>
            <span className="logo-pill">Free</span>
          </a>
          <nav className="nav-links" aria-label="Sections">
            <a href="#editor">Editor</a>
            <a href="#previewTitle">Preview</a>
            <a href="#score-checker">ATS score</a>
            <a href="#faq">FAQ</a>
          </nav>
          <div className="nav-cta">
            <span className="saved-flash" data-visible={savedFlash} aria-hidden="true">
              Draft saved ✓
            </span>
            {/* Live region twin of the visual flash: the animated span only
                toggles CSS opacity (no text change), so screen readers would
                never hear it — this one gets real content to announce. */}
            <span className="visually-hidden" role="status">
              {savedFlash ? "Draft saved" : ""}
            </span>
            <span
              className={`conn ${apiHealthy === null ? "pending" : apiHealthy ? "on" : "off"}`}
              title={
                apiHealthy === null
                  ? "Checking the CV service…"
                  : apiHealthy
                    ? "CV service is reachable"
                    : "Cannot reach the CV service right now"
              }
            >
              <i className="dot" aria-hidden="true" />
              {apiHealthy === null ? "Checking…" : apiHealthy ? "API ready" : "API offline"}
            </span>
            <Btn variant="ghost" onClick={loadSample}>
              See an example
            </Btn>
            <Btn
              variant="primary"
              onClick={() => handleGenerate("docx")}
              loading={status === "loading"}
              disabled={status === "loading"}
            >
              {status === "loading" ? "Generating…" : "Download"}
            </Btn>
          </div>
        </div>
      </header>

      <section className="hero">
        <div className="hero-inner">
          <h1>
            Free ATS CV in <span className="hl">2 minutes</span> — no signup.
          </h1>
          <p className="lede">
            Type on the left, watch a real A4 CV appear on the right, download a
            clean Word file. Student or senior — pick the structure that fits you.
          </p>
          <div className="chips" role="list">
            <span className="chip" role="listitem">
              <i className="dot ok" aria-hidden="true" />
              No login
            </span>
            <span className="chip" role="listitem">
              <i className="dot ok" aria-hidden="true" />
              Real .docx
            </span>
            <span className="chip" role="listitem">
              <i className="dot ok" aria-hidden="true" />
              No stored CVs
            </span>
          </div>
          <a className="btn btn-primary hero-cta" href="#editor">
            Build my CV — it's free
          </a>
          <p className="hero-sample">
            New here?{" "}
            <button type="button" className="link-btn" onClick={loadSample}>
              See a filled example
            </button>
          </p>
        </div>
      </section>

      <div className="workspace" id="editor">
        <div className="editor-col">
          <SectionNavDefault cv={cv} />

          <main
            className={`editor ${mobileTab === "editor" ? "tab-active" : ""}`}
            aria-label="CV editor"
          >
            {draftInfo !== null ? (
              <div className="restore-banner" role="status">
                <span>
                  Welcome back! You have an unsaved draft from{" "}
                  {draftAgeMinutes(draftInfo) === 0
                    ? "just now"
                    : `${draftAgeMinutes(draftInfo)} min ago`}{" "}
                  (stored only in this browser).
                </span>
                <span className="restore-actions">
                  <Btn variant="soft" onClick={restoreDraft}>
                    Restore draft
                  </Btn>
                  <Btn variant="ghost" onClick={discardDraft}>
                    Discard
                  </Btn>
                </span>
              </div>
            ) : null}

            {importOpen ? (
              <SectionCard
                title="Import an existing CV"
                subtitle="Upload your DOCX or PDF and keep editing here."
              >
                <ImportCV onImport={applyImported} hasExistingData={hasContent(cv)} />
              </SectionCard>
            ) : (
              <p className="import-teaser">
                Have a CV already?{" "}
                <button
                  type="button"
                  className="link-btn"
                  onClick={() => setImportOpen(true)}
                >
                  Import it instead of typing
                </button>
              </p>
            )}

            <SectionCard
              id="score-checker"
              title="Check any CV's ATS score"
              subtitle="Already have a CV you like? Score it before you rebuild it — nothing is saved and your editor stays untouched."
            >
              <ScoreChecker />
            </SectionCard>

            <SectionCard
              id={SECTION_IDS.profile}
              title="Who is this CV for?"
              subtitle="Pick the structure — you can change it any time. Content is never lost."
            >
              <ProfilePicker value={profile.key} onChange={setProfile} />
            </SectionCard>

            <SectionCard
              id={SECTION_IDS.personal}
              title="Personal information"
              subtitle="Name, title & contact details."
            >
              <PersonalForm cv={cv} problems={problems} update={update} />
              <NextSection targetId={SECTION_IDS.summary} label="Summary" />
            </SectionCard>

            <SectionCard
              id={SECTION_IDS.summary}
              title={profile.key === "fresher" ? "Career objective" : "Professional summary"}
              subtitle="3–5 sentences, plain text."
            >
              <SummaryForm cv={cv} update={update} />
              <NextSection targetId={SECTION_IDS.skills} label="Skills" />
            </SectionCard>

            <SectionCard
              id={SECTION_IDS.skills}
              title="Skills"
              subtitle="Type a skill and press Enter. Exported as document keywords."
            >
              <SkillsForm cv={cv} update={update} />
              <NextSection
                targetId={nextIdAfter("skills", ["skills", ...profile.middleSections])}
                label={labelAfter("skills", ["skills", ...profile.middleSections])}
              />
            </SectionCard>

            {middleCards}

            <SectionCard
              id={SECTION_IDS.extras}
              title="Extras"
              subtitle="Certifications, languages and anything else."
              actions={
                <Btn
                  variant="soft"
                  onClick={() => addItem("certifications", emptyCertification())}
                >
                  + Add certification
                </Btn>
              }
            >
              <ExtrasForm cv={cv} update={update} />
              <NextSection targetId={SECTION_IDS.template} label="Style" />
            </SectionCard>

            <SectionCard
              id={SECTION_IDS.template}
              title="Template"
              subtitle="Pick a look — the preview updates instantly. Content stays the same."
            >
              <TemplatePicker value={cv.template} onChange={(template) => update({ template })} />
              <NextSection targetId={SECTION_IDS.review} label="Download" />
            </SectionCard>

            <SectionCard
              id={SECTION_IDS.review}
              title="Review & download"
              subtitle="Check the paper, then export."
            >
              <p className="privacy">
                Your entries are sent to the API only to build the file —
                processed in memory and never stored. Your draft lives in
                this browser.
              </p>
              <div className="download-row">
                <Btn
                  size="lg"
                  onClick={() => handleGenerate("docx")}
                  loading={status === "loading"}
                  disabled={status === "loading"}
                >
                  <span className="btn-label">
                    {status === "loading" ? "Generating…" : "Download Word (.docx)"}
                  </span>
                </Btn>
                <Btn
                  size="lg"
                  variant="soft"
                  onClick={() => handleGenerate("pdf")}
                  loading={status === "loading"}
                  disabled={status === "loading"}
                >
                  <span className="btn-label">
                    {status === "loading" ? "Generating…" : "Download PDF"}
                  </span>
                </Btn>
              </div>
          <StatusBanner status={status} message={message} />
              {status === "success" ? (
                <div className="success">
                  <div>
                    <strong>Done! Your CV is downloaded.</strong>
                    <span> {downloadName} saved to downloads.</span>
                  </div>
                  {/* Share moment: role="status" so the 2s "Link copied!"
                      label swap is announced to screen readers. */}
                  <span className="success-actions" role="status">
                    <Btn variant="soft" onClick={copyShareLink}>
                      {shareCopied ? "Link copied!" : "Copy share link"}
                    </Btn>
                    <Btn variant="ghost" onClick={resetForm}>
                      Clear and restart
                    </Btn>
                  </span>
                </div>
              ) : null}
              {status === "success" && genScorePhase === "offer" ? (
                <div className="gen-score-offer">
                  <span>Wondering how recruiting software reads it?</span>
                  <Btn variant="soft" onClick={scoreGenerated}>
                    Check its ATS score
                  </Btn>
                </div>
              ) : null}
              {status === "success" && genScorePhase === "checking" ? (
                <p className="import-note" role="status">
                  Reading your CV…
                </p>
              ) : null}
              {status === "success" && genScorePhase === "shown" && genScore ? (
                <ScoreCard
                  score={genScore}
                  useLabel="Improve it here →"
                  onUse={() => scrollToSection(SECTION_IDS.personal)}
                />
              ) : null}
              {status === "success" && genScorePhase === "failed" ? (
                <div className="gen-score-offer" role="status">
                  <span>Couldn't score it this time.</span>
                  <Btn variant="ghost" onClick={scoreGenerated}>
                    Try again
                  </Btn>
                </div>
              ) : null}
              {submitted && !isCVValid(problems) && status !== "loading" ? (
                <div className="problems" role="alert">
                  <strong>Please fix:</strong>
                  <ul>
                    {Object.entries(problems)
                      .filter(([, p]) => p)
                      .map(([key, p]) => (
                        <li key={key}>{p}</li>
                      ))}
                  </ul>
                </div>
              ) : null}
              {/* Non-blocking quality cautions: shown after a download attempt
                  (or once submitted), never preventing the file. */}
              {submitted && status !== "loading" ? (
                Object.values(warnings).some((w) => w) ? (
                  <div className="cautions">
                    <strong>Worth improving:</strong>
                    <ul>
                      {Object.values(warnings)
                        .filter((w) => w)
                        .map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                    </ul>
                  </div>
                ) : null
              ) : null}
            </SectionCard>
          </main>
        </div>

        <aside
          className={`preview-side ${mobileTab === "preview" ? "tab-active" : ""}`}
          aria-label="Live preview"
        >
          <div className="preview-bar">
            <h2 id="previewTitle">Live preview</h2>
            <span className="live">
              <i className="pulse" aria-hidden="true" />
              updates as you type
            </span>
          </div>
          <ATSChecks cv={cv} />
          <div className="paper">
            <CVPreview cv={cv} />
          </div>
        </aside>
      </div>

      {/* Mobile-only Editor/Preview switch — plain toggle buttons: a
          tablist role would promise arrow-key navigation that this simple
          two-button switch does not provide. */}
      <div
        className={`mobile-tabs ${keyboardOpen ? "kb-hidden" : ""}`}
        aria-label="Editor or preview"
      >
        <button
          type="button"
          aria-pressed={mobileTab === "editor"}
          className={mobileTab === "editor" ? "on" : ""}
          onClick={() => setMobileTab("editor")}
        >
          Editor
        </button>
        <button
          type="button"
          aria-pressed={mobileTab === "preview"}
          className={mobileTab === "preview" ? "on" : ""}
          onClick={() => setMobileTab("preview")}
        >
          Preview
        </button>
      </div>

      <section className="faq" id="faq">
        <h2>Questions, answered</h2>
        {/* "What's the catch?" is the objection free tools never answer
            out loud — leading with it preempts the scam suspicion. */}
        <details open>
          <summary>What's the catch?</summary>
          <p>Nothing. No ads, no account, no upsell. It just works.</p>
        </details>
        <details>
          <summary>Do I need an account?</summary>
          <p>No. No login, no signup, no paywall.</p>
        </details>
        <details>
          <summary>Is the file really ATS-friendly?</summary>
          <p>
            Yes — single column, standard headings, real bullets and text. No
            boxes, graphics or photos.
          </p>
        </details>
        <details>
          <summary>I'm a student with no work experience. Can I still use this?</summary>
          <p>
            Yes — choose <strong>Fresher / Entry-level</strong> at the top. Your
            education and projects move to the front, work experience becomes
            optional, and the summary becomes a career objective.
          </p>
        </details>
        <details>
          <summary>What format do I get?</summary>
          <p>
            A clean <strong>.docx</strong> Word file you can edit and upload
            anywhere.
          </p>
        </details>
        <details>
          <summary>Do you store my data?</summary>
          <p>
            No accounts, no database, no stored CVs. Your entries are sent
            to the API only to build the file, processed in memory and never
            saved. A draft stays in this browser so a refresh doesn't eat
            your work; "Clear and restart" wipes it.
          </p>
        </details>
      </section>

      <footer className="footer">
        <div className="footer-brand">
          <span className="logo-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z" />
            </svg>
          </span>
          <span className="footer-name">ATS CV Generator</span>
        </div>
        <p className="footer-tag">
          Build a clean, professional CV in minutes and download it as a Word
          file. Free, no signup.
        </p>
        <nav className="footer-links" aria-label="Footer">
          <a href="#editor">Editor</a>
          <a
            href="#score-checker"
            onClick={(e) => {
              e.preventDefault();
              goToScoreChecker();
            }}
          >
            ATS score checker
          </a>
          <a href="#faq">FAQ</a>
          <a href="#/privacy">Privacy Policy</a>
          <a href="#/terms">Terms of Service</a>
        </nav>
        <span className="footer-credit">
          © {new Date().getFullYear()}{" "}
          <a
            className="footer-credit-link"
            href="https://faysalmahmudprem.com"
            target="_blank"
            rel="noopener noreferrer"
          >
            Faysal Mahmud Prem
          </a>
          {" "}· Licensed under Apache-2.0
        </span>
      </footer>

      <div className={`sticky-cta ${keyboardOpen ? "kb-hidden" : ""}`}>
        <Btn
          size="lg"
          onClick={() => handleGenerate("docx")}
          loading={status === "loading"}
          disabled={status === "loading"}
        >
          {status === "loading" ? "Generating…" : "Download CV"}
        </Btn>
      </div>
    </>
  );
}
