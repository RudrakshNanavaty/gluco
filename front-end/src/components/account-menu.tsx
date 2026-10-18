"use client";

import { LogOutIcon } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAppSession } from "@/lib/app-session";

function initials(name: string) {
  const words = name
    .replace(/[^\p{L}\p{N} ]/gu, "")
    .split(" ")
    .filter(Boolean);
  const last = words.at(-1) ?? "?";
  return /\d/.test(last)
    ? last.slice(-2)
    : words
        .map((w) => w[0])
        .join("")
        .slice(0, 2);
}

export function AccountMenu() {
  const session = useAppSession();
  if (session.status !== "signed-in") return null;
  const { principal, signOut } = session;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="gap-2 px-1.5"
            aria-label={`Account: ${principal.display_name}`}
          >
            <Avatar className="size-6">
              <AvatarFallback className="text-[0.65rem]">
                {initials(principal.display_name)}
              </AvatarFallback>
            </Avatar>
            <span className="hidden sm:inline">{principal.display_name}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="flex flex-col">
            <span>{principal.display_name}</span>
            <span className="text-xs font-normal text-muted-foreground">
              {principal.role === "clinician" ? "Clinician" : "Patient"}
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem onSelect={signOut}>
              <LogOutIcon />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </>
  );
}
