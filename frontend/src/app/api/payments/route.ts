import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import crypto from "crypto";

const PLANS = {
  starter: { amount: 99900, credits: 25 }, // ₹999
  pro: { amount: 249900, credits: 100 }, // ₹2,499
  enterprise: { amount: 999900, credits: 500 }, // ₹9,999
} as const;

type PlanKey = keyof typeof PLANS;

export async function POST(request: NextRequest) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { plan, action } = await request.json();

  if (action === "create-order") {
    if (!plan || !(plan in PLANS)) {
      return NextResponse.json({ error: "Invalid plan" }, { status: 400 });
    }

    const planConfig = PLANS[plan as PlanKey];

    // Create Razorpay order via their API (server-side only)
    const razorpayAuth = Buffer.from(
      `${process.env.RAZORPAY_KEY_ID}:${process.env.RAZORPAY_KEY_SECRET}`
    ).toString("base64");

    const orderRes = await fetch("https://api.razorpay.com/v1/orders", {
      method: "POST",
      headers: {
        Authorization: `Basic ${razorpayAuth}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        amount: planConfig.amount,
        currency: "INR",
        receipt: `filebrsr_${user.id}_${Date.now()}`,
        notes: {
          user_id: user.id,
          plan,
        },
      }),
    });

    if (!orderRes.ok) {
      return NextResponse.json(
        { error: "Failed to create order" },
        { status: 500 }
      );
    }

    const order = await orderRes.json();

    // Record payment in database
    await supabase.from("payments").insert({
      user_id: user.id,
      razorpay_order_id: order.id,
      amount: planConfig.amount,
      plan,
      status: "created",
    });

    return NextResponse.json({
      orderId: order.id,
      amount: planConfig.amount,
      currency: "INR",
      keyId: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID,
    });
  }

  if (action === "verify-payment") {
    const { razorpay_order_id, razorpay_payment_id, razorpay_signature } =
      await request.json();

    // Verify signature server-side
    const expectedSignature = crypto
      .createHmac("sha256", process.env.RAZORPAY_KEY_SECRET!)
      .update(`${razorpay_order_id}|${razorpay_payment_id}`)
      .digest("hex");

    if (expectedSignature !== razorpay_signature) {
      return NextResponse.json(
        { error: "Payment verification failed" },
        { status: 400 }
      );
    }

    // Update payment record
    await supabase
      .from("payments")
      .update({
        razorpay_payment_id,
        razorpay_signature,
        status: "paid",
      })
      .eq("razorpay_order_id", razorpay_order_id);

    // Get the plan from the payment record
    const { data: payment } = await supabase
      .from("payments")
      .select("plan")
      .eq("razorpay_order_id", razorpay_order_id)
      .single();

    if (payment && payment.plan in PLANS) {
      const credits = PLANS[payment.plan as PlanKey].credits;
      const { data: profile } = await supabase
        .from("profiles")
        .select("credits_remaining")
        .eq("id", user.id)
        .single();

      await supabase
        .from("profiles")
        .update({
          plan: payment.plan,
          credits_remaining: (profile?.credits_remaining || 0) + credits,
        })
        .eq("id", user.id);
    }

    return NextResponse.json({ success: true });
  }

  return NextResponse.json({ error: "Invalid action" }, { status: 400 });
}
