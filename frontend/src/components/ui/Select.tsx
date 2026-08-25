import * as RadixSelect from "@radix-ui/react-select";
import { IconChevronDown, IconCheck } from "@tabler/icons-react";
import type { Icon } from "@tabler/icons-react";
import { forwardRef } from "react";
import { cn } from "./utils";

export type SelectOption = {
  label: string;
  value: string;
};

type SelectProps = {
  ariaLabel: string;
  className?: string;
  disabled?: boolean;
  id?: string;
  leadingIcon?: Icon;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  value: string;
};

export const Select = forwardRef<HTMLButtonElement, SelectProps>(function Select(
  { ariaLabel, className, disabled, id, leadingIcon: LeadingIcon, onValueChange, options, placeholder = "请选择", value },
  ref,
) {
  return (
    <RadixSelect.Root disabled={disabled} onValueChange={onValueChange} value={value}>
      <RadixSelect.Trigger
        ref={ref}
        aria-label={ariaLabel}
        className={cn("ui-select", className)}
        data-slot="select-trigger"
        id={id}
      >
        {LeadingIcon ? <LeadingIcon aria-hidden="true" className="ui-select-leading-icon" size={15} /> : null}
        <RadixSelect.Value placeholder={placeholder} />
        <RadixSelect.Icon asChild>
          <IconChevronDown size={16} />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content className="ui-select-content" data-slot="select-content" position="popper" sideOffset={6}>
          <RadixSelect.Viewport className="ui-select-viewport" data-slot="select-viewport">
            {options.map((option) => (
              <RadixSelect.Item className="ui-select-item" data-slot="select-item" key={option.value} value={option.value}>
                <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
                <RadixSelect.ItemIndicator className="ui-select-item-indicator">
                  <IconCheck size={14} />
                </RadixSelect.ItemIndicator>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
});
