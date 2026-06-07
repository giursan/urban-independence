"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { DEV_USER_ID } from "@/lib/dev";
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

const CARD =
  "rounded-2xl border border-border bg-card p-5 shadow-sm";
const INPUT =
  "w-full rounded-xl border border-border bg-background px-4 py-3 text-base focus:border-primary";
const LABEL = "block text-sm font-semibold uppercase tracking-wide text-muted";

function emptyFact(): FactDraft {
  return {
    category: "family",
    title: "",
    content: "",
    tags: "",
    importance: 3,
  };
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

  function updateProfile<K extends keyof ProfileDraft>(key: K, value: ProfileDraft[K]) {
    setProfile((current) => ({ ...current, [key]: value }));
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
      .eq("id", DEV_USER_ID);
    setSavingProfile(false);
    if (updateError) {
      setError(updateError.message);
      return;
    }
    setNotice("Persona updated.");
    router.refresh();
  }

  async function addFact(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.title.trim() || !draft.content.trim()) {
      setError("Title and detail are required for a knowledge entry.");
      return;
    }
    setSavingFact(true);
    setError("");
    setNotice("");
    const supabase = createClient();
    const payload = {
      user_id: DEV_USER_ID,
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
    setNotice("Knowledge entry added.");
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
    setNotice("Knowledge entry removed.");
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
      setError("Title and detail are required for a knowledge entry.");
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
    setNotice("Knowledge entry updated.");
  }

  return (
    <main className="mx-auto grid w-full max-w-6xl flex-1 gap-5 px-4 py-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(20rem,0.85fr)]">
      <section className="space-y-5">
        <div className={CARD}>
          <h1 className="text-3xl font-bold tracking-tight">Companion brief</h1>
          <p className="mt-2 max-w-2xl text-base leading-relaxed text-muted">
            Shape how the companion knows this person: their name, rhythms, important
            relationships, sensitive areas, and what usually helps the conversation land well.
          </p>
        </div>

        <form onSubmit={saveProfile} className={`${CARD} space-y-5`}>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="preferred_name" className={LABEL}>
                Preferred name
              </label>
              <input
                id="preferred_name"
                value={profile.preferred_name}
                onChange={(e) => updateProfile("preferred_name", e.target.value)}
                className={INPUT}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="interests" className={LABEL}>
                Interests
              </label>
              <input
                id="interests"
                value={profile.interests}
                onChange={(e) => updateProfile("interests", e.target.value)}
                placeholder="gardening, choir, football"
                className={INPUT}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="family" className={LABEL}>
                Family and important people
              </label>
              <textarea
                id="family"
                value={profile.family}
                onChange={(e) => updateProfile("family", e.target.value)}
                rows={4}
                className={INPUT}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="career" className={LABEL}>
                Work and life story
              </label>
              <textarea
                id="career"
                value={profile.career}
                onChange={(e) => updateProfile("career", e.target.value)}
                rows={4}
                className={INPUT}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="hometown" className={LABEL}>
                Hometown and places
              </label>
              <textarea
                id="hometown"
                value={profile.hometown}
                onChange={(e) => updateProfile("hometown", e.target.value)}
                rows={3}
                className={INPUT}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="routines" className={LABEL}>
                Daily routines
              </label>
              <textarea
                id="routines"
                value={profile.routines}
                onChange={(e) => updateProfile("routines", e.target.value)}
                rows={3}
                className={INPUT}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="sensitivities" className={LABEL}>
                Sensitivities
              </label>
              <textarea
                id="sensitivities"
                value={profile.sensitivities}
                onChange={(e) => updateProfile("sensitivities", e.target.value)}
                rows={3}
                className={INPUT}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="topics_to_avoid" className={LABEL}>
                Topics to avoid
              </label>
              <textarea
                id="topics_to_avoid"
                value={profile.topics_to_avoid}
                onChange={(e) => updateProfile("topics_to_avoid", e.target.value)}
                rows={3}
                className={INPUT}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="conversation_style" className={LABEL}>
                Conversation style
              </label>
              <textarea
                id="conversation_style"
                value={profile.conversation_style}
                onChange={(e) => updateProfile("conversation_style", e.target.value)}
                rows={4}
                className={INPUT}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="companion_brief" className={LABEL}>
                Caregiver brief
              </label>
              <textarea
                id="companion_brief"
                value={profile.companion_brief}
                onChange={(e) => updateProfile("companion_brief", e.target.value)}
                rows={4}
                className={INPUT}
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={savingProfile}
              className="rounded-xl bg-primary px-5 py-3 text-base font-semibold text-primary-foreground disabled:opacity-50"
            >
              {savingProfile ? "Saving..." : "Save persona"}
            </button>
            {notice ? <p className="text-sm text-accent">{notice}</p> : null}
            {error ? <p className="text-sm text-danger">{error}</p> : null}
          </div>
        </form>
      </section>

      <section className="space-y-5">
        <form onSubmit={addFact} className={`${CARD} space-y-4`}>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Knowledge bank</h2>
            <p className="mt-2 text-base leading-relaxed text-muted">
              Add concrete facts the agent can retrieve with a tool call during conversation.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="fact_category" className={LABEL}>
                Category
              </label>
              <select
                id="fact_category"
                value={draft.category}
                onChange={(e) => setDraft((current) => ({ ...current, category: e.target.value }))}
                className={INPUT}
              >
                <option value="family">Family</option>
                <option value="routine">Routine</option>
                <option value="preference">Preference</option>
                <option value="memory">Life memory</option>
                <option value="health">Comfort and care</option>
                <option value="topic">Conversation topic</option>
              </select>
            </div>
            <div className="space-y-2">
              <label htmlFor="fact_importance" className={LABEL}>
                Importance
              </label>
              <input
                id="fact_importance"
                type="range"
                min={1}
                max={5}
                value={draft.importance}
                onChange={(e) =>
                  setDraft((current) => ({ ...current, importance: Number(e.target.value) }))
                }
                className="w-full accent-primary"
              />
              <p className="text-sm text-muted">Priority {draft.importance} of 5</p>
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="fact_title" className={LABEL}>
              Short label
            </label>
            <input
              id="fact_title"
              value={draft.title}
              onChange={(e) => setDraft((current) => ({ ...current, title: e.target.value }))}
              placeholder="Daughter Mia"
              className={INPUT}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="fact_content" className={LABEL}>
              Detail the companion should know
            </label>
            <textarea
              id="fact_content"
              value={draft.content}
              onChange={(e) => setDraft((current) => ({ ...current, content: e.target.value }))}
              rows={5}
              placeholder="Mia is her daughter, lives in Bristol, and usually calls on Sundays."
              className={INPUT}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="fact_tags" className={LABEL}>
              Search tags
            </label>
            <input
              id="fact_tags"
              value={draft.tags}
              onChange={(e) => setDraft((current) => ({ ...current, tags: e.target.value }))}
              placeholder="mia, daughter, sunday"
              className={INPUT}
            />
          </div>

          <button
            type="submit"
            disabled={savingFact}
            className="w-full rounded-xl bg-accent px-5 py-3 text-base font-semibold text-white disabled:opacity-50"
          >
            {savingFact ? "Adding..." : "Add knowledge entry"}
          </button>
        </form>

        <div className={`${CARD} space-y-4`}>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-2xl font-bold tracking-tight">Saved entries</h2>
            <span className="text-sm text-muted">{facts.length} stored</span>
          </div>

          {facts.length === 0 ? (
            <p className="text-base leading-relaxed text-muted">
              No companion facts yet. Add names, routines, favorite subjects, calming prompts,
              or family context the agent should be able to pull in when needed.
            </p>
          ) : (
            <div className="space-y-3">
              {facts.map((fact) => (
                <article key={fact.id} className="rounded-xl border border-border bg-background p-4">
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
                            <option value="family">Family</option>
                            <option value="routine">Routine</option>
                            <option value="preference">Preference</option>
                            <option value="memory">Life memory</option>
                            <option value="health">Comfort and care</option>
                            <option value="topic">Conversation topic</option>
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
                            className="w-full accent-primary"
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
                          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
                        >
                          {savingFact ? "Saving..." : "Save changes"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingId(null)}
                          className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-muted hover:bg-card"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-accent">
                            {fact.category}
                          </p>
                          <h3 className="mt-1 text-lg font-semibold">{fact.title}</h3>
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => beginEdit(fact)}
                            className="rounded-lg border border-border px-3 py-2 text-sm font-semibold text-muted hover:bg-card"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteFact(fact.id)}
                            className="rounded-lg border border-border px-3 py-2 text-sm font-semibold text-muted hover:bg-card"
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
                            className="rounded-lg border border-border px-2 py-1 text-sm text-muted"
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
    </main>
  );
}
