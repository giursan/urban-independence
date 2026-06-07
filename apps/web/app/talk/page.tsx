import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { DEV_USER_ID } from "@/lib/dev";
import { AppNav } from "@/components/AppNav";
import { ConversationWorkspace } from "@/components/ConversationWorkspace";

export default async function TalkPage() {
  const supabase = await createClient();

  const { data: profile } = await supabase
    .from("profiles")
    .select("preferred_name, onboarded")
    .eq("id", DEV_USER_ID)
    .maybeSingle();

  if (profile && profile.onboarded === false) redirect("/onboarding");

  const name = profile?.preferred_name ?? null;
  const greeting = name
    ? `Hello ${name}. I'm so glad you're here. What's on your mind today?`
    : `Hello, I'm so glad you're here. What's on your mind today?`;

  return (
    <div className="flex flex-1 flex-col">
      <AppNav userName={name} />
      <ConversationWorkspace greeting={greeting} />
    </div>
  );
}
