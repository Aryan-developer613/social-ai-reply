/**
 * Auto Pipeline → Workflow redirect
 *
 * The standalone auto-pipeline page has been merged into the unified
 * /app/workflow page. This file keeps old bookmarks and direct links
 * from 404-ing by immediately redirecting.
 */
import { redirect } from "next/navigation";

export default function AutoPipelineRedirect() {
  redirect("/app/workflow");
}
