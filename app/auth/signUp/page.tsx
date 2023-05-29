import { Container } from "app/components/common/boxes/container";
import ButtonPrimary from "app/components/common/buttons/button-primary";
import TextInputField from "app/components/common/inputs/TextInputField";
import Link from "next/link";
import { IoMdArrowBack } from "react-icons/io";

const SignUp = () => {
  return (
    <Container>
      <div className="flex flex-col pt-[7vh] gap-16">
        <Link href="/">
          <IoMdArrowBack className="h-8 w-8" />
        </Link>
        <div className="flex flex-col items-center">
          <p className="text-4xl font-title">KaraMonke</p>
          <p className="text-lg">Your ultimate song collector</p>
        </div>

        <div className="flex flex-col items-center gap-3">
          <div className="flex flex-col w-full gap-2">
            <TextInputField header="Username" sampleText={"Your Username"} type="text" />
            <TextInputField header="Email" sampleText={"hello@gmail.com"} type="email" />
            <TextInputField header="Password" sampleText={""} type="password" />
            <TextInputField header="Confirm Password" sampleText={""} type="password" />
          </div>
        </div>

        <div className="flex flex-col items-center">
          <ButtonPrimary className="w-full mb-3">
            <p>Sign Up</p>
          </ButtonPrimary>
          <div className="flex">
            <p className="text-sm mr-1">Already have an account?</p>
            <Link href="/auth/login">
              <p className="text-sm underline text-primary-600">Login</p>
            </Link>
          </div>
        </div>
      </div>
    </Container>
  );
};

export default SignUp;
