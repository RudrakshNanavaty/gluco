"use client"

import { PageContainer } from "@/components/page-container"
import { PatientDashboard } from "@/components/patient/patient-dashboard"
import { RoleGate } from "@/components/role-gate"
import { useAppSession } from "@/lib/app-session"

export default function PatientPage() {
  const session = useAppSession()
  return (
    <RoleGate role="patient">
      <PageContainer>
        {session.status === "signed-in" ? (
          <PatientDashboard principal={session.principal} />
        ) : null}
      </PageContainer>
    </RoleGate>
  )
}
