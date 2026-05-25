import { Construction } from "lucide-react";

interface Props {
  title: string;
  body: string;
}

export function StepStub({ title, body }: Props) {
  return (
    <div className="mx-auto max-w-2xl rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center shadow-sm">
      <Construction className="mx-auto h-10 w-10 text-amber-500" />
      <h2 className="mt-3 text-base font-semibold text-slate-900">{title}</h2>
      <p className="mt-2 text-sm text-slate-600">{body}</p>
      <p className="mt-4 text-xs text-slate-400">
        Implementation in progress. See the project plan for build order.
      </p>
    </div>
  );
}
