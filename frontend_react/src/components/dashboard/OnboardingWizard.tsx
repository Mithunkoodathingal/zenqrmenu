import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Crown, Settings, Utensils, Check, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface OnboardingWizardProps {
  currentStep: 1 | 2;
  onGoToRestaurant: () => void;
}

const steps = [
  { icon: Crown, label: "Choose a Plan", description: "Pick the plan that suits your restaurant" },
  { icon: Settings, label: "Set Up Restaurant", description: "Add your restaurant details" },
  { icon: Utensils, label: "Manage Menu", description: "Start adding your menu items" },
];

const OnboardingWizard = ({ currentStep, onGoToRestaurant }: OnboardingWizardProps) => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div className="max-w-lg w-full text-center">
        <h1 className="text-3xl font-bold font-heading mb-2">Welcome to Zen Menu! 🎉</h1>
        <p className="text-muted-foreground mb-8">Let's get your restaurant set up in a few quick steps.</p>

        {/* Steps indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {steps.map((step, i) => {
            const stepNum = i + 1;
            const isComplete = stepNum < currentStep;
            const isActive = stepNum === currentStep;

            return (
              <div key={step.label} className="flex items-center gap-2">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                    isComplete
                      ? "bg-primary text-primary-foreground"
                      : isActive
                        ? "bg-primary/20 text-primary ring-2 ring-primary"
                        : "bg-muted text-muted-foreground"
                  }`}
                >
                  {isComplete ? <Check className="h-4 w-4" /> : stepNum}
                </div>
                {i < steps.length - 1 && (
                  <div className={`h-0.5 w-8 ${stepNum < currentStep ? "bg-primary" : "bg-muted"}`} />
                )}
              </div>
            );
          })}
        </div>

        {/* Active step card */}
        <Card className="p-8 shadow-card">
          {currentStep === 1 && (
            <>
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mx-auto mb-4">
                <Crown className="h-8 w-8 text-primary" />
              </div>
              <h2 className="text-xl font-bold font-heading mb-2">Choose Your Plan</h2>
              <p className="text-muted-foreground mb-6">
                Select a plan to unlock tables, menu items, and premium features for your restaurant.
              </p>
              <Button variant="hero" size="lg" className="w-full" onClick={() => navigate("/pricing")}>
                View Plans & Choose <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </>
          )}

          {currentStep === 2 && (
            <>
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mx-auto mb-4">
                <Settings className="h-8 w-8 text-primary" />
              </div>
              <h2 className="text-xl font-bold font-heading mb-2">Set Up Your Restaurant</h2>
              <p className="text-muted-foreground mb-6">
                Add your restaurant name, logo, and contact details so customers can find you.
              </p>
              <Button variant="hero" size="lg" className="w-full" onClick={onGoToRestaurant}>
                Go to Restaurant Settings <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </>
          )}
        </Card>
      </div>
    </div>
  );
};

export default OnboardingWizard;
