"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import type { CompanionFact } from "@/lib/types";

type ProfileDraft = {
  preferred_name: string;
  interests: string;
  family: string;
  hometown: string;
  career: string;
  routines: string;
  sensitivities: string;
  conversation_style: string;
  topics_to_avoid: string;
  companion_brief: string;
};

type FactDraft = {
  category: string;
  title: string;
  content: string;
  tags: string;
  importance: number;
};

type SecurityQuestion = { id: string; question: string; created_by: string };

const SECTION = "border-t border-border py-8";
const INPUT =
  "w-full rounded-xl border border-border bg-white px-4 py-3 text-base shadow-none focus:border-primary";
const LABEL = "block text-sm font-semibold text-muted";
const SECONDARY_BUTTON =
  "rounded-xl border border-border bg-white px-5 py-3 text-base font-semibold hover:bg-background disabled:opacity-50";
const PRIMARY_BUTTON =
  "rounded-xl bg-foreground px-5 py-3 text-base font-semibold text-white hover:bg-black disabled:opacity-50";

function emptyFact(): FactDraft {
  return {
    category: "family",
    title: "",
    content: "",
    tags: "",
    importance: 3,
  };
}

function categoryOptions() {
  return (
    <>
      <option value="family">Family</option>
      <option value="routine">Routine</option>
      <option value="preference">Preference</option>
      <option value="memory">Life memory</option>
      <option value="health">Comfort and care</option>
      <option value="topic">Conversation topic</option>
    </>
  );
}

export function CaregiverWorkspace({
  initialProfile,
  initialFacts,
}: {
  initialProfile: ProfileDraft;
  initialFacts: CompanionFact[];
}) {
  const router = useRouter();
  const [profile, setProfile] = useState(initialProfile);
  const [facts, setFacts] = useState(initialFacts);
  const [draft, setDraft] = useState<FactDraft>(emptyFact());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<FactDraft>(emptyFact());
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingFact, setSavingFact] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [phone, setPhone] = useState("");
  const [savingPhone, setSavingPhone] = useState(false);
  const [securityQuestions, setSecurityQuestions] = useState<SecurityQuestion[]>([]);
  const [questionDraft, setQuestionDraft] = useState({ question: "", answer: "" });
  const [savingQuestion, setSavingQuestion] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(({ data }) => setUserId(data.user?.id ?? null));
    apiFetch("/security-questions")
      .then((res) => (res.ok ? res.json() : []))
      .then((rows) => setSecurityQuestions(rows as SecurityQuestion[]))
      .catch(() => {});
  }, []);

  function updateProfile<K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) {
    setProfile((current) => ({ ...current, [key]: value }));
  }

  async function savePhone(e: React.FormEvent) {
    e.preventDefault();
    setSavingPhone(true);
    setError("");
    setNotice("");
    const res = await apiFetch("/profile/phone", {
      method: "PUT",
      body: JSON.stringify({ phone }),
    });
    setSavingPhone(false);
    if (!res.ok) {
      setError("Could not save the phone number.");
      return;
    }
    setNotice("Phone number registered.");
  }

  async function addQuestion(e: React.FormEvent) {
    e.preventDefault();
    if (!questionDraft.question.trim() || !questionDraft.answer.trim()) {
      setError("A question and answer are both required.");
      return;
    }
    setSavingQuestion(true);
    setError("");
    setNotice("");
    const res = await apiFetch("/security-questions", {
      method: "POST",
      body: JSON.stringify({ ...questionDraft, created_by: "caregiver" }),
    });
    setSavingQuestion(false);
    if (!res.ok) {
      setError("Could not add the security question.");
      return;
    }
    const created = (await res.json()) as SecurityQuestion;
    setSecurityQuestions((current) => [...current, created]);
    setQuestionDraft({ question: "", answer: "" });
    setNotice("Security question added.");
  }

  async function removeQuestion(id: string) {
    setError("");
    setNotice("");
    const res = await apiFetch(`/security-questions/${id}`, { method: "DELETE" });
    if (!res.ok) {
      setError("Could not remove the security question.");
      return;
    }
    setSecurityQuestions((current) => current.filter((q) => q.id !== id));
    setNotice("Security question removed.");
  }

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSavingProfile(true);
    setError("");
    setNotice("");
    const supabase = createClient();
    const { error: updateError } = await supabase
      .from("profiles")
      .update({
        preferred_name: profile.preferred_name || null,
        interests: profile.interests
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        life_context: {
          family: profile.family || undefined,
          hometown: profile.hometown || undefined,
          career: profile.career || undefined,
          routines: profile.routines || undefined,
          sensitivities: profile.sensitivities || undefined,
          conversation_style: profile.conversation_style || undefined,
          topics_to_avoid: profile.topics_to_avoid || undefined,
          companion_brief: profile.companion_brief || undefined,
        },
        onboarded: true,
      })
      .eq("id", userId);
    setSavingProfile(false);
    if (updateError) {
      setError(updateError.message);
      return;
    }
    setNotice("Profile updated.");
    router.refresh();
  }

  async function addFact(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.title.trim() || !draft.content.trim()) {
      setError("Title and detail are required for a memory.");
      return;
    }
    setSavingFact(true);
    setError("");
    setNotice("");
    const supabase = createClient();
    const payload = {
      user_id: userId,
      category: draft.category,
      title: draft.title.trim(),
      content: draft.content.trim(),
      tags: draft.tags
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      importance: draft.importance,
    };
    const { data, error: insertError } = await supabase
      .from("companion_facts")
      .insert(payload)
      .select("id, category, title, content, tags, importance, updated_at")
      .single();
    setSavingFact(false);
    if (insertError) {
      setError(insertError.message);
      return;
    }
    setFacts((current) => [data as CompanionFact, ...current]);
    setDraft(emptyFact());
    setNotice("Memory added.");
  }

  async function deleteFact(id: string) {
    setError("");
    setNotice("");
    const supabase = createClient();
    const { error: deleteError } = await supabase.from("companion_facts").delete().eq("id", id);
    if (deleteError) {
      setError(deleteError.message);
      return;
    }
    setFacts((current) => current.filter((fact) => fact.id !== id));
    setNotice("Memory removed.");
  }

  function beginEdit(fact: CompanionFact) {
    setEditingId(fact.id);
    setEditDraft({
      category: fact.category,
      title: fact.title,
      content: fact.content,
      tags: fact.tags.join(", "),
      importance: fact.importance,
    });
    setError("");
    setNotice("");
  }

  async function saveEdit(id: string) {
    if (!editDraft.title.trim() || !editDraft.content.trim()) {
      setError("Title and detail are required for a memory.");
      return;
    }
    setSavingFact(true);
    setError("");
    setNotice("");
    const supabase = createClient();
    const payload = {
      category: editDraft.category,
      title: editDraft.title.trim(),
      content: editDraft.content.trim(),
      tags: editDraft.tags
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      importance: editDraft.importance,
    };
    const { data, error: updateError } = await supabase
      .from("companion_facts")
      .update(payload)
      .eq("id", id)
      .select("id, category, title, content, tags, importance, updated_at")
      .single();
    setSavingFact(false);
    if (updateError) {
      setError(updateError.message);
      return;
    }
    setFacts((current) => current.map((fact) => (fact.id === id ? (data as CompanionFact) : fact)));
    setEditingId(null);
    setNotice("Memory updated.");
  }

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-5 sm:px-6 sm:py-6">
      <section className="rounded-[1.25rem] bg-card px-5 py-6 sm:px-8 sm:py-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-muted">Care profile</p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight">
              {profile.preferred_name || "Companion profile"}
            </h1>
            <p className="mt-3 max-w-2xl text-lg leading-relaxed text-muted">
              Keep the companion grounded in the person&apos;s routines, relationships, and
              preferences.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 text-sm text-muted">
            <span>{facts.length} memories</span>
            <span>{securityQuestions.length} security questions</span>
          </div>
        </div>

        {notice || error ? (
          <div className="mt-6 rounded-xl bg-background px-4 py-3 text-base">
            {notice ? <p className="font-medium text-accent">{notice}</p> : null}
            {error ? <p className="font-medium text-danger">{error}</p> : null}
          </div>
        ) : null}

        <form onSubmit={saveProfile} className={SECTION}>
          <div className="grid gap-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
            <div>
              <h2 className="text-xl font-semibold">Personal details</h2>
              <p className="mt-2 text-base leading-relaxed text-muted">
                Basics the companion can use naturally.
              </p>
            </div>
            <div className="space-y-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label htmlFor="preferred_name" className={LABEL}>Preferred name</label>
                  <input
                    id="preferred_name"
                    value={profile.preferred_name}
                    onChange={(e) => updateProfile("preferred_name", e.target.value)}
                    className={INPUT}
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="interests" className={LABEL}>Interests</label>
                  <input
                    id="interests"
                    value={profile.interests}
                    onChange={(e) => updateProfile("interests", e.target.value)}
                    placeholder="gardening, choir, football"
                    className={INPUT}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="family" className={LABEL}>Family and important people</label>
                <textarea
                  id="family"
                  value={profile.family}
                  onChange={(e) => updateProfile("family", e.target.value)}
                  rows={4}
                  className={INPUT}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label htmlFor="hometown" className={LABEL}>Hometown and places</label>
                  <textarea
                    id="hometown"
                    value={profile.hometown}
                    onChange={(e) => updateProfile("hometown", e.target.value)}
                    rows={3}
                    className={INPUT}
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="career" className={LABEL}>Work and life story</label>
                  <textarea
                    id="career"
                    value={profile.career}
                    onChange={(e) => updateProfile("career", e.target.value)}
                    rows={3}
                    className={INPUT}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 grid gap-8 border-t border-border pt-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
            <div>
              <h2 className="text-xl font-semibold">Conversation</h2>
              <p className="mt-2 text-base leading-relaxed text-muted">
                Tone, comfort, and boundaries.
              </p>
            </div>
            <div className="space-y-5">
              <div className="space-y-2">
                <label htmlFor="routines" className={LABEL}>Daily routines</label>
                <textarea
                  id="routines"
                  value={profile.routines}
                  onChange={(e) => updateProfile("routines", e.target.value)}
                  rows={3}
                  className={INPUT}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label htmlFor="sensitivities" className={LABEL}>Sensitivities</label>
                  <textarea
                    id="sensitivities"
                    value={profile.sensitivities}
                    onChange={(e) => updateProfile("sensitivities", e.target.value)}
                    rows={3}
                    className={INPUT}
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="topics_to_avoid" className={LABEL}>Topics to avoid</label>
                  <textarea
                    id="topics_to_avoid"
                    value={profile.topics_to_avoid}
                    onChange={(e) => updateProfile("topics_to_avoid", e.target.value)}
                    rows={3}
                    className={INPUT}
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label htmlFor="conversation_style" className={LABEL}>Conversation style</label>
                  <textarea
                    id="conversation_style"
                    value={profile.conversation_style}
                    onChange={(e) => updateProfile("conversation_style", e.target.value)}
                    rows={4}
                    className={INPUT}
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="companion_brief" className={LABEL}>Caregiver brief</label>
                  <textarea
                    id="companion_brief"
                    value={profile.companion_brief}
                    onChange={(e) => updateProfile("companion_brief", e.target.value)}
                    rows={4}
                    className={INPUT}
                  />
                </div>
              </div>

              <button type="submit" disabled={savingProfile} className={PRIMARY_BUTTON}>
                {savingProfile ? "Saving..." : "Save profile"}
              </button>
            </div>
          </div>
        </form>

        <section className={SECTION}>
          <div className="grid gap-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
            <div>
              <h2 className="text-xl font-semibold">Phone identity</h2>
              <p className="mt-2 text-base leading-relaxed text-muted">
                Recognize trusted callers and protect personal context.
              </p>
            </div>

            <div className="space-y-6">
              <form onSubmit={savePhone} className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
                <div className="space-y-2">
                  <label htmlFor="phone" className={LABEL}>Registered phone number</label>
                  <input
                    id="phone"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+1 555 555 0100"
                    className={INPUT}
                  />
                </div>
                <button type="submit" disabled={savingPhone} className={`${SECONDARY_BUTTON} self-end`}>
                  {savingPhone ? "Saving..." : "Save number"}
                </button>
              </form>

              <form onSubmit={addQuestion} className="space-y-3">
                <label className={LABEL}>Add a security question</label>
                <input
                  value={questionDraft.question}
                  onChange={(e) =>
                    setQuestionDraft((current) => ({ ...current, question: e.target.value }))
                  }
                  placeholder="What was your first pet's name?"
                  className={INPUT}
                />
                <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
                  <input
                    value={questionDraft.answer}
                    onChange={(e) =>
                      setQuestionDraft((current) => ({ ...current, answer: e.target.value }))
                    }
                    placeholder="Answer"
                    className={INPUT}
                  />
                  <button type="submit" disabled={savingQuestion} className={SECONDARY_BUTTON}>
                    {savingQuestion ? "Adding..." : "Add"}
                  </button>
                </div>
              </form>

              <div className="divide-y divide-border rounded-xl border border-border bg-white">
                {securityQuestions.length === 0 ? (
                  <p className="px-4 py-3 text-base text-muted">No security questions yet.</p>
                ) : (
                  securityQuestions.map((q) => (
                    <div key={q.id} className="flex items-center justify-between gap-3 px-4 py-3">
                      <span className="text-base">{q.question}</span>
                      <button
                        type="button"
                        onClick={() => removeQuestion(q.id)}
                        className="rounded-lg px-3 py-2 text-sm font-semibold text-muted hover:bg-background"
                      >
                        Remove
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>

        <form onSubmit={addFact} className={SECTION}>
          <div className="grid gap-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
            <div>
              <h2 className="text-xl font-semibold">Memories</h2>
              <p className="mt-2 text-base leading-relaxed text-muted">
                Add details the companion should remember.
              </p>
            </div>

            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label htmlFor="fact_category" className={LABEL}>Category</label>
                  <select
                    id="fact_category"
                    value={draft.category}
                    onChange={(e) =>
                      setDraft((current) => ({ ...current, category: e.target.value }))
                    }
                    className={INPUT}
                  >
                    {categoryOptions()}
                  </select>
                </div>
                <div className="space-y-2">
                  <label htmlFor="fact_importance" className={LABEL}>Importance</label>
                  <input
                    id="fact_importance"
                    type="range"
                    min={1}
                    max={5}
                    value={draft.importance}
                    onChange={(e) =>
                      setDraft((current) => ({ ...current, importance: Number(e.target.value) }))
                    }
                    className="w-full accent-foreground"
                  />
                  <p className="text-sm text-muted">Priority {draft.importance} of 5</p>
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="fact_title" className={LABEL}>Short label</label>
                <input
                  id="fact_title"
                  value={draft.title}
                  onChange={(e) => setDraft((current) => ({ ...current, title: e.target.value }))}
                  placeholder="Daughter Mia"
                  className={INPUT}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="fact_content" className={LABEL}>Detail</label>
                <textarea
                  id="fact_content"
                  value={draft.content}
                  onChange={(e) =>
                    setDraft((current) => ({ ...current, content: e.target.value }))
                  }
                  rows={4}
                  placeholder="Mia is her daughter, lives in Bristol, and usually calls on Sundays."
                  className={INPUT}
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
                <div className="space-y-2">
                  <label htmlFor="fact_tags" className={LABEL}>Search tags</label>
                  <input
                    id="fact_tags"
                    value={draft.tags}
                    onChange={(e) => setDraft((current) => ({ ...current, tags: e.target.value }))}
                    placeholder="mia, daughter, sunday"
                    className={INPUT}
                  />
                </div>
                <button type="submit" disabled={savingFact} className={`${PRIMARY_BUTTON} self-end`}>
                  {savingFact ? "Adding..." : "Add memory"}
                </button>
              </div>
            </div>
          </div>
        </form>

        <section className={SECTION}>
          <div className="grid gap-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
            <div>
              <h2 className="text-xl font-semibold">Saved memories</h2>
              <p className="mt-2 text-base text-muted">{facts.length} stored</p>
            </div>

            {facts.length === 0 ? (
              <p className="rounded-xl border border-border bg-white px-4 py-4 text-base leading-relaxed text-muted">
                No memories yet.
              </p>
            ) : (
              <div className="divide-y divide-border rounded-xl border border-border bg-white">
                {facts.map((fact) => (
                  <article key={fact.id} className="p-4">
                    {editingId === fact.id ? (
                      <div className="space-y-4">
                        <div className="grid gap-4 sm:grid-cols-2">
                          <div className="space-y-2">
                            <label className={LABEL}>Category</label>
                            <select
                              value={editDraft.category}
                              onChange={(e) =>
                                setEditDraft((current) => ({ ...current, category: e.target.value }))
                              }
                              className={INPUT}
                            >
                              {categoryOptions()}
                            </select>
                          </div>
                          <div className="space-y-2">
                            <label className={LABEL}>Priority</label>
                            <input
                              type="range"
                              min={1}
                              max={5}
                              value={editDraft.importance}
                              onChange={(e) =>
                                setEditDraft((current) => ({
                                  ...current,
                                  importance: Number(e.target.value),
                                }))
                              }
                              className="w-full accent-foreground"
                            />
                          </div>
                        </div>
                        <div className="space-y-2">
                          <label className={LABEL}>Short label</label>
                          <input
                            value={editDraft.title}
                            onChange={(e) =>
                              setEditDraft((current) => ({ ...current, title: e.target.value }))
                            }
                            className={INPUT}
                          />
                        </div>
                        <div className="space-y-2">
                          <label className={LABEL}>Detail</label>
                          <textarea
                            rows={4}
                            value={editDraft.content}
                            onChange={(e) =>
                              setEditDraft((current) => ({ ...current, content: e.target.value }))
                            }
                            className={INPUT}
                          />
                        </div>
                        <div className="space-y-2">
                          <label className={LABEL}>Search tags</label>
                          <input
                            value={editDraft.tags}
                            onChange={(e) =>
                              setEditDraft((current) => ({ ...current, tags: e.target.value }))
                            }
                            className={INPUT}
                          />
                        </div>
                        <div className="flex flex-wrap gap-3">
                          <button
                            type="button"
                            onClick={() => saveEdit(fact.id)}
                            disabled={savingFact}
                            className={PRIMARY_BUTTON}
                          >
                            {savingFact ? "Saving..." : "Save changes"}
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className={SECONDARY_BUTTON}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-muted">{fact.category}</p>
                            <h3 className="mt-1 text-lg font-semibold">{fact.title}</h3>
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => beginEdit(fact)}
                              className="rounded-lg px-3 py-2 text-sm font-semibold text-muted hover:bg-background"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              onClick={() => deleteFact(fact.id)}
                              className="rounded-lg px-3 py-2 text-sm font-semibold text-muted hover:bg-background"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                        <p className="mt-2 text-base leading-relaxed">{fact.content}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {fact.tags.map((tag) => (
                            <span
                              key={`${fact.id}-${tag}`}
                              className="rounded-full bg-background px-3 py-1 text-sm text-muted"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                        <p className="mt-3 text-sm text-muted">
                          Priority {fact.importance}/5 · Updated{" "}
                          {new Date(fact.updated_at).toLocaleDateString(undefined, {
                            dateStyle: "medium",
                          })}
                        </p>
                      </>
                    )}
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>
      </section>
    </main>
  );
}
