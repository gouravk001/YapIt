import { typeStyle } from "../lib/noteTypes";

const SIZES = {
  sm: { box: "h-8 w-8 rounded-lg", icon: 16 },
  md: { box: "h-10 w-10 rounded-xl", icon: 19 },
};

export default function TypeIcon({ typeName, size = "md" }) {
  const { icon: Icon, tile } = typeStyle(typeName);
  const { box, icon } = SIZES[size];
  return (
    <span className={`flex shrink-0 items-center justify-center ring-1 ring-inset ${box} ${tile}`}>
      <Icon size={icon} aria-hidden="true" />
    </span>
  );
}
