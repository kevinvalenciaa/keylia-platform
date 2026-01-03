import { initTRPC, TRPCError } from "@trpc/server";
import superjson from "superjson";
import { ZodError } from "zod";
import { createClient } from "@/lib/supabase/server";
import { User } from "@supabase/supabase-js";

// Use 'any' for supabase to avoid complex type inference issues with tRPC context
// The actual types are defined in lib/supabase/types.ts but don't flow through tRPC properly
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SupabaseAny = any;

// Explicitly type the context
interface TRPCContext {
  supabase: SupabaseAny;
  user: User | null;
  headers: Headers;
}

export const createTRPCContext = async (opts: { headers: Headers }): Promise<TRPCContext> => {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return {
    supabase,
    user,
    headers: opts.headers,
  };
};

const t = initTRPC.context<TRPCContext>().create({
  transformer: superjson,
  errorFormatter({ shape, error }) {
    return {
      ...shape,
      data: {
        ...shape.data,
        zodError:
          error.cause instanceof ZodError ? error.cause.flatten() : null,
      },
    };
  },
});

export const createCallerFactory = t.createCallerFactory;
export const createTRPCRouter = t.router;

// Public procedure - no auth required
export const publicProcedure = t.procedure;

// Protected procedure - requires authenticated user
export const protectedProcedure = t.procedure.use(async ({ ctx, next }) => {
  if (!ctx.user) {
    throw new TRPCError({ code: "UNAUTHORIZED" });
  }
  return next({
    ctx: {
      ...ctx,
      user: ctx.user,
    },
  });
});
