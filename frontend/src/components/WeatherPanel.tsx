import { useCountUp } from "@/components/motion/useCountUp";
import { cn } from "@/lib/utils";
import {
  CloudSun,
  Droplets,
  Eye,
  Gauge,
  MapPin,
  Snowflake,
  Sun,
  Thermometer,
  Wind,
} from "lucide-react";

const METRICS = [
  { label: "Humidité", value: "62%", hint: "Confortable", icon: Droplets, fill: 62 },
  { label: "Vent", value: "18 km/h", hint: "SSO · modéré", icon: Wind, fill: 45 },
  { label: "UV", value: "4 / 11", hint: "Modéré", icon: Sun, fill: 36 },
  { label: "Visibilité", value: "12 km", hint: "Claire", icon: Eye, fill: 80 },
];

export function WeatherPanel({ className }: { className?: string }) {
  const [tempRef, temp] = useCountUp(14);
  const [feelsRef, feels] = useCountUp(12);

  return (
    <div
      className={cn(
        "weather-panel relative isolate overflow-hidden rounded-3xl text-[#F4FAF6]",
        className,
      )}
    >
      <div className="weather-sky pointer-events-none absolute inset-0" aria-hidden>
        <span className="weather-cloud weather-cloud-a" />
        <span className="weather-cloud weather-cloud-b" />
        <span className="weather-cloud weather-cloud-c" />
        <span className="weather-haze" />
        <div className="weather-horizon" />
        <div className="weather-field-lines">
          {Array.from({ length: 7 }).map((_, i) => (
            <span key={i} style={{ ["--i" as string]: i }} />
          ))}
        </div>
      </div>

      <div className="relative z-10 flex h-full flex-col p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/12 px-3 py-1.5 text-xs font-semibold backdrop-blur-md ring-1 ring-white/20">
            <MapPin className="h-3.5 w-3.5 text-[#E8C04A]" />
            Chartres · Eure-et-Loir
            <span className="weather-live-dot ml-1" />
            <span className="text-white/70 font-medium">Live</span>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full bg-[#1C2B1C]/25 px-3 py-1.5 text-xs font-medium backdrop-blur-md ring-1 ring-white/15">
            <CloudSun className="h-3.5 w-3.5" />
            Éclaircies · vent modéré
          </div>
        </div>

        <div className="mt-5 flex flex-1 flex-col gap-6 md:mt-6 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/55">
              Aujourd’hui sur la parcelle
            </p>
            <div className="mt-1 flex items-end gap-3">
              <span
                ref={tempRef}
                className="font-display text-[4.5rem] leading-none font-semibold tracking-tight drop-shadow-sm md:text-[5.25rem]"
              >
                {temp}°
              </span>
              <div className="mb-2 space-y-1">
                <p className="text-sm text-white/75">
                  Ressenti{" "}
                  <span ref={feelsRef} className="font-semibold text-white">
                    {feels}°
                  </span>
                </p>
                <p className="inline-flex items-center gap-1.5 text-xs text-[#E8C04A]">
                  <Thermometer className="h-3.5 w-3.5" />
                  Max 16° · Min 3°
                </p>
              </div>
            </div>

            <div className="mt-4 inline-flex max-w-md items-start gap-2.5 rounded-2xl bg-[#1C2B1C]/30 px-3.5 py-2.5 text-sm backdrop-blur-md ring-1 ring-[#E8C04A]/35">
              <Snowflake className="mt-0.5 h-4 w-4 shrink-0 text-[#E8C04A]" />
              <p className="leading-snug text-white/90">
                <span className="font-semibold text-[#E8C04A]">Gel prévu cette nuit</span>
                {" - "}jusqu’à −2°C entre 3h et 6h. Surveillez les jeunes plants.
              </p>
            </div>
          </div>

          <div className="weather-orb relative mx-auto flex h-36 w-36 shrink-0 items-center justify-center md:mx-0 md:h-40 md:w-40">
            <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 120 120" aria-hidden>
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                stroke="rgba(255,255,255,0.15)"
                strokeWidth="8"
              />
              <circle
                className="weather-orb-arc"
                cx="60"
                cy="60"
                r="52"
                fill="none"
                stroke="url(#weatherOrbGrad)"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 52}`}
                strokeDashoffset={`${2 * Math.PI * 52 * (1 - 0.72)}`}
              />
              <defs>
                <linearGradient id="weatherOrbGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#E8C04A" />
                  <stop offset="100%" stopColor="#7EC8A3" />
                </linearGradient>
              </defs>
            </svg>
            <div className="relative text-center">
              <Gauge className="mx-auto h-5 w-5 text-[#E8C04A]" />
              <p className="mt-1 font-display text-2xl font-semibold leading-none">Bon</p>
              <p className="mt-1 text-[10px] uppercase tracking-wider text-white/60">
                Indice parcelle
              </p>
            </div>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          {METRICS.map((m) => {
            const Icon = m.icon;
            return (
              <div
                key={m.label}
                className="group rounded-2xl bg-white/10 px-3 py-3 backdrop-blur-md ring-1 ring-white/15 transition duration-300 hover:-translate-y-0.5 hover:bg-white/16"
              >
                <div className="flex items-center justify-between gap-2">
                  <Icon className="h-4 w-4 text-[#E8C04A] transition-transform duration-400 group-hover:scale-110" />
                  <span className="text-[10px] font-medium uppercase tracking-wide text-white/50">
                    {m.label}
                  </span>
                </div>
                <p className="mt-1.5 font-display text-lg font-semibold leading-none">{m.value}</p>
                <p className="mt-1 text-[11px] text-white/60">{m.hint}</p>
                <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/15">
                  <div
                    className="weather-meter-fill h-full rounded-full bg-gradient-to-r from-[#E8C04A] to-[#7EC8A3]"
                    style={{ width: `${m.fill}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
}
