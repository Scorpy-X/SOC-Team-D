import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Check, CircleHelp, PencilLine, ShieldCheck } from "lucide-react"

export default function ReviewWorkspace() {
  const selectedBand = props.bands?.find((band) => band.id === props.selected_band_id)

  return (
    <div className="mt-4 space-y-4">
      <Card className="soc-surface-card">
        <CardHeader className="space-y-3 pb-4">
          <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary" className="soc-chip bg-primary/10 text-primary">
              Review
            </Badge>
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Advisor preview
            </span>
          </div>
          <div className="space-y-2">
            <CardTitle className="text-2xl tracking-tight">{props.title}</CardTitle>
            <CardDescription className="max-w-3xl text-sm leading-6 text-muted-foreground">
              {props.intro}
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <section className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Recorded answers
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Use edit to jump back to a question without losing the saved session.
                </p>
              </div>
              <div className="soc-chip border-0 bg-muted/60 text-foreground">
                {props.answers?.length || 0} answers saved
              </div>
            </div>
            <div className="space-y-3">
              {(props.answers || []).map((answer) => (
                <div
                  key={answer.question_id}
                  className="soc-surface-soft rounded-2xl px-4 py-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Question {answer.order}
                      </div>
                      <div className="text-sm font-semibold text-foreground">
                        {answer.label}
                      </div>
                      <p className="text-sm leading-6 text-muted-foreground">
                        {answer.value}
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="rounded-full"
                      onClick={() =>
                        callAction({
                          name: "review_edit_answer",
                          payload: { questionId: answer.question_id },
                        })
                      }
                    >
                      <PencilLine className="size-4" />
                      Edit
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <Separator />

          <section className="space-y-4">
            <div className="space-y-1">
              <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Calculated profile and optional override
              </h3>
              <p className="text-sm text-muted-foreground">
                The highlighted profile is calculated from the questionnaire unless you choose a different one as an advisor review override.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {(props.bands || []).map((band) => {
                const selected = band.id === props.selected_band_id
                return (
                  <Card
                    key={band.id}
                    className={
                      "border transition-colors " +
                      (selected
                        ? "border-primary bg-primary/10 shadow-[0_14px_34px_rgba(80,151,214,0.18)]"
                        : "border-border/70 bg-card/70")
                    }
                  >
                    <CardHeader className="space-y-3 pb-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                            Band {band.order}
                          </div>
                          <CardTitle className="mt-1 text-lg tracking-tight">
                            {band.label}
                          </CardTitle>
                        </div>
                        {selected ? (
                          <Badge className="rounded-full bg-primary text-primary-foreground">
                            <Check className="mr-1 size-3.5" />
                            Selected
                          </Badge>
                        ) : null}
                      </div>
                      <CardDescription className="text-sm leading-6 text-muted-foreground">
                        {band.description}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4 pt-0">
                      <p className="text-xs leading-5 text-muted-foreground">
                        {band.range_summary}
                      </p>
                      <Button
                        variant={selected ? "secondary" : "outline"}
                        className="w-full rounded-full"
                        onClick={() =>
                          callAction({
                            name: "review_select_band",
                            payload: { bandId: band.id },
                          })
                        }
                      >
                        {selected ? "Active profile" : "Use as override"}
                      </Button>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </section>

            <div className="soc-surface-soft rounded-2xl px-4 py-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                  <ShieldCheck className="size-4 text-primary" />
                  Ready for the risk check
                </div>
                <p className="text-sm leading-6 text-muted-foreground">
                  {props.selected_band_id
                    ? `Selected profile: ${props.selected_band_label}. ${props.selected_band_help}`
                    : props.selected_band_help}
                </p>
              </div>
              <Button
                className="rounded-full px-5"
                disabled={!props.can_confirm}
                onClick={() =>
                  callAction({
                    name: "review_continue_to_risk_check",
                    payload: {},
                  })
                }
              >
                Continue to risk check
              </Button>
            </div>
          </div>

          <div className="rounded-2xl border border-border/60 bg-background/30 px-4 py-3 text-sm text-muted-foreground">
            <div className="flex items-start gap-2">
              <CircleHelp className="mt-0.5 size-4 shrink-0" />
              <p>{props.fallback_hint}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
