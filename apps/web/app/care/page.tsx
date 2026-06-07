import { redirect } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { CaregiverWorkspace } from "@/components/CaregiverWorkspace";
import { createClient } from "@/lib/supabase/server";
import type { CompanionFact } from "@/lib/types";

function asText(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export default async function CarePage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("preferred_name, interests, life_context")
    .eq("id", user.id)
    .maybeSingle();

  const { data: facts } = await supabase
    .from("companion_facts")
    .select("id, category, title, content, tags, importance, updated_at")
    .eq("user_id", user.id)
    .order("updated_at", { ascending: false });

  const lifeContext = (profile?.life_context as Record<string, unknown> | null) ?? {};
  const initialProfile = {
    preferred_name: asText(profile?.preferred_name),
    interests: Array.isArray(profile?.interests) ? profile.interests.join(", ") : "",
    family: asText(lifeContext.family),
    hometown: asText(lifeContext.hometown),
    career: asText(lifeContext.career),
    routines: asText(lifeContext.routines),
    sensitivities: asText(lifeContext.sensitivities),
    conversation_style: asText(lifeContext.conversation_style),
    topics_to_avoid: asText(lifeContext.topics_to_avoid),
    companion_brief: asText(lifeContext.companion_brief),
  };

  return (
    <div className="flex flex-1 flex-col">
      <AppNav userName={profile?.preferred_name} />
      <CaregiverWorkspace
        initialProfile={initialProfile}
        initialFacts={(facts as CompanionFact[] | null) ?? []}
      />
    </div>
  );
}
