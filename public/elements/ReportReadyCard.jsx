import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FileText, RotateCcw, Sparkles } from "lucide-react"
import { useEffect, useRef } from "react"

export default function ReportReadyCard() {
  const cardRef = useRef(null)

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      cardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
    })

    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <div ref={cardRef} className="mt-4 space-y-4">
      <Card className="soc-surface-card">
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="soc-chip bg-primary/10 text-primary">
              {props.eyebrow}
            </Badge>
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Detailed report attached below
            </span>
          </div>
          <div className="space-y-2">
            <CardTitle className="text-2xl tracking-tight">{props.title}</CardTitle>
            <CardDescription className="max-w-3xl text-sm leading-6 text-muted-foreground">
              {props.summary}
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="soc-note-grid two-up">
            {(props.highlights || []).map((item) => (
              <div key={item.label} className="soc-surface-soft rounded-2xl px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  {item.label}
                </div>
                <div className="mt-2 text-xl font-semibold tracking-tight text-foreground">
                  {item.value}
                </div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.detail}</p>
              </div>
            ))}
          </div>

          <section className="space-y-3">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  Investments selected
                </h3>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {props.investment_note}
                </p>
              </div>
            </div>
            <div className="space-y-3">
              {(props.investment_groups || []).map((group) => (
                <div key={group.label} className="soc-surface-soft rounded-2xl px-4 py-4">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <h4 className="text-sm font-semibold text-foreground">{group.label}</h4>
                    <span className="soc-chip border-0 bg-background/50 text-xs text-muted-foreground">
                      {group.total_weight_label}
                    </span>
                  </div>
                  <div className="space-y-3">
                    {(group.holdings || []).map((holding) => (
                      <div
                        key={holding.asset_code}
                        className="grid gap-1 border-t border-border/50 pt-3 first:border-t-0 first:pt-0 md:grid-cols-[minmax(0,1fr)_auto]"
                      >
                        <div className="min-w-0">
                          <div className="text-sm font-semibold text-foreground">
                            {holding.asset_code} - {holding.weight_label}
                          </div>
                          <div className="mt-1 text-xs leading-5 text-muted-foreground">
                            {holding.detail}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="rounded-2xl border border-border/60 bg-background/30 px-4 py-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                  <FileText className="size-4 text-primary" />
                  {props.report_name}
                </div>
                <ul className="space-y-2 text-sm leading-6 text-muted-foreground">
                  {(props.next_steps || []).map((item) => (
                    <li key={item} className="list-inside list-disc">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  className="rounded-full px-5"
                  onClick={() =>
                    callAction({
                      name: "report_show_preview",
                      payload: {},
                    })
                  }
                >
                  <Sparkles className="size-4" />
                  See report summary
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full px-5"
                  onClick={() =>
                    callAction({
                      name: "restart_chat",
                      payload: {},
                    })
                  }
                >
                  <RotateCcw className="size-4" />
                  Start over
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
