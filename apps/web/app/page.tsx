import Link from "next/link";
import Image from "next/image";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center px-5 py-10 sm:py-16">
      <section className="grid items-center gap-10 rounded-[1.25rem] bg-card p-6 sm:p-10 md:grid-cols-[1fr_18rem]">
        <div>
          <p className="text-base font-semibold text-muted">Companion</p>
          <h1 className="mt-3 text-5xl font-semibold leading-tight tracking-tight text-foreground">
            A friend to talk with, any time.
          </h1>
          <p className="mt-5 max-w-2xl text-2xl leading-relaxed text-foreground">
            A warm, patient chat for sharing your day, remembering happy moments, and staying
            connected.
          </p>
          <Link
            href="/talk"
            className="mt-8 inline-flex min-h-16 items-center rounded-xl bg-foreground px-9 py-4 text-2xl font-semibold text-white hover:bg-black"
          >
            Start talking
          </Link>
        </div>
        <div className="flex aspect-square items-center justify-center rounded-2xl bg-background p-5">
          <Image
            src="/icon.svg"
            alt=""
            width={320}
            height={320}
            className="h-full w-full rounded-[1.2rem] object-cover"
            priority
          />
        </div>
      </section>
    </main>
  );
}
