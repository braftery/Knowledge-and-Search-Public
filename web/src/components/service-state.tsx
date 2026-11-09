import { TriangleAlert } from "lucide-react";
import { Button } from "@/components/button";
import { Icon } from "@/components/icon";

export function ServiceError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="hh-empty" role="alert">
      <h3>The knowledge service did not respond</h3>
      <p>{message}</p>
      {onRetry ? (
        <Button variant="secondary" compact onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function InlineProblem({ message }: { message: string }) {
  return (
    <p className="hh-error" role="alert">
      <Icon icon={TriangleAlert} />
      {message}
    </p>
  );
}
