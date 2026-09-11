import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  imgClassName?: string;
  /** Soft plate behind the mark (sidebar / light UI). Use "none" for bare logo. */
  plate?: "none" | "light" | "dark";
};

/** JoyClub brand symbol — footprint / tradition-meets-technology mark */
export function BrandMark({ className, imgClassName, plate = "light" }: Props) {
  return (
    <div
      className={cn(
        "grid shrink-0 place-items-center overflow-hidden",
        plate !== "none" && "rounded-xl",
        plate === "light" && "bg-white shadow-sm ring-1 ring-black/5",
        plate === "dark" && "bg-white/15 backdrop-blur rounded-xl",
        className,
      )}
    >
      <img
        src="/account/logo-mark.png?v=20260911"
        alt="JoyClub Associate"
        className={cn(
          "h-full w-full object-contain",
          plate === "none" ? "p-0" : "p-1",
          imgClassName,
        )}
      />
    </div>
  );
}
